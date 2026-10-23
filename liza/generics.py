"""Whole-program monomorphization, preserving declaration-site access rights.

The cache contains canonical declaration/type/capacity keys, never layouts.
Bodies are checked by the ordinary lowerer after substitution. No executable
ModuleIR is returned until every discovered specialization has passed checking.
"""
import copy
from dataclasses import fields, is_dataclass, replace
import hashlib
import json
from .frontend import CompileError, Expr, Statement, Struct
from .types import is_array, is_view, element_type, type_application


class Signatures(dict):
    pass


class Monomorphizer:
    LIMIT = 256
    DEPTH = 32

    def __init__(self, program):
        self.program = program
        self.templates = {}
        seen = {}
        for declaration in list(program)+program.structs+program.enums:
            name=declaration.name.text
            if name in seen:
                previous = seen[name]
                if hasattr(previous, 'body') != hasattr(declaration, 'body'):
                    message = 'function and structure names must be distinct'
                else:
                    message = 'duplicate function' if hasattr(declaration, 'body') else 'duplicate structure or enum'
                raise CompileError(declaration.name, message)
            seen[name] = declaration
            if getattr(declaration,'generic_params',[]): self.templates[name]=declaration
        self.functions = [f for f in program if not f.generic_params]
        program[:] = self.functions
        program.structs = [s for s in program.structs if not s.generic_params]
        self.cache, self.instances, self.type_keys = {}, [], {}
        self.structs, self.signatures, self.current_chain = None, None, []
        self.bound_checks = []
        # Iterate over a snapshot: instantiating a field appends concrete types.
        for declaration in list(program.structs):
            declaration.fields=[(t,self.concrete_type(v,t)) for t,v in declaration.fields]
        for declaration in program.enums:
            declaration.cases=[(t,self.concrete_type(v,t) if v else None) for t,v in declaration.cases]
        for function in self.functions: self.prepare(function,{})

    def trace(self, error, chain=None):
        chain=self.current_chain if chain is None else chain
        if not chain or getattr(error,'specialized',False): return error
        result=CompileError(chain[-1]['token'], 'specialization: '+ ' -> '.join(c['label'] for c in chain)+'\n  '+str(error))
        result.specialized=True
        return result

    def display(self, t):
        if t in self.type_keys:
            name,args=self.type_keys[t]
            return name+'<'+','.join(self.display(a) for a in args)+'>'
        if is_array(t): return '['+self.display(element_type(t))+';'+t[1:-1].rsplit(';',1)[1]+']'
        app=type_application(t)
        if app:return app[0]+'<'+','.join(self.display(a) for a in app[1])+'>'
        return t

    def substitute(self, t, mapping):
        if t in mapping:return mapping[t]
        if is_array(t):
            element,count=t[1:-1].rsplit(';',1)
            return '['+self.substitute(element,mapping)+';'+mapping.get(count,count)+']'
        app=type_application(t)
        if app:return app[0]+'<'+','.join(self.substitute(a,mapping) for a in app[1])+'>'
        return t

    def concrete_type(self,t,token):
        if is_array(t):
            element,count=t[1:-1].rsplit(';',1)
            if not count.isdigit() or int(count)>4294967295:
                raise CompileError(token,'capacity must be a compile-time u32')
            return '['+self.concrete_type(element,token)+';'+str(int(count))+']'
        app=type_application(t)
        if app:
            name,args=app
            if name in ('View','Option','Result'):
                return name+'<'+','.join(self.concrete_type(a,token) for a in args)+'>'
            declaration=self.templates.get(name)
            if not isinstance(declaration,Struct):raise CompileError(token,'unknown generic type '+name)
            return self.instantiate(declaration,args,token).name.text
        if t in self.templates: raise CompileError(token,'generic type requires arguments: '+t)
        return t

    def prepare(self, function, mapping):
        function.params=[(token,self.concrete_type(self.substitute(t,mapping),token)) for token,t in function.params]
        function.result_type=self.concrete_type(self.substitute(function.result_type,mapping),function.name)
        def walk(node):
            if isinstance(node,Expr):
                if node.kind=='name' and node.token.text in mapping:
                    replacement=mapping[node.token.text]
                    if not replacement.isdigit():raise CompileError(node.token,'type parameter is not a value')
                    literal = Expr(replace(node.token, text=replacement), 'literal', [])
                    node.kind = 'convert.checked'
                    node.token = replace(node.token, text='u32')
                    node.args = [literal]
                node.type_args=[self.substitute(t,mapping) for t in node.type_args]
                for arg in node.args:walk(arg)
            elif isinstance(node,Statement):
                if node.annotation:node.annotation=self.concrete_type(self.substitute(node.annotation,mapping),node.token)
                walk(node.expr)
            elif isinstance(node,list):
                for item in node:walk(item)
            elif is_dataclass(node):
                for field in fields(node):
                    if field.name not in ('token','name'):walk(getattr(node,field.name))
        walk(function.body)

    def instantiate(self, declaration, arguments, token):
        params=declaration.generic_params
        if len(params)!=len(arguments): raise CompileError(token,'wrong number of generic arguments for '+declaration.name.text)
        args=[]
        for parameter,argument in zip(params,arguments):
            if parameter.kind=='u32':
                if not argument.isdigit() or int(argument)>4294967295:
                    raise CompileError(token,'capacity argument must be a compile-time u32')
                args.append(str(int(argument)))
            else:
                if argument.isdigit():raise CompileError(token,'expected type argument')
                args.append(self.concrete_type(argument,token))
        key=(declaration.name.text,tuple(args))
        if key in self.cache:return self.cache[key]
        kind='type' if isinstance(declaration,Struct) else 'function'
        label=declaration.name.text+'<'+','.join(self.display(a) for a in args)+'>'
        chain=self.current_chain+[{'key':key,'label':label,'token':token}]
        if any(item['key'][0]==key[0] for item in self.current_chain):
            raise self.trace(CompileError(token,'expanding/polymorphic recursion is not supported'),chain)
        if len(self.cache)>=self.LIMIT or len(chain)>self.DEPTH:
            raise self.trace(CompileError(token,'specialization limit exceeded'),chain)
        symbol='liza$'+kind+'$'+hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()
        clone=copy.deepcopy(declaration)
        clone.name=replace(declaration.name,text=symbol)
        clone.generic_params=[];clone.instantiation_chain=chain
        self.cache[key]=clone
        self.instances.append({'declaration':key[0],'arguments':args,'kind':kind,'symbol':symbol})
        mapping={p.token.text:a for p,a in zip(params,args)}
        previous=self.current_chain;self.current_chain=chain
        try:
            if kind=='type':
                self.type_keys[symbol]=key
                clone.fields=[(t,self.concrete_type(self.substitute(v,mapping),t)) for t,v in clone.fields]
                self.program.structs.append(clone)
                if self.structs is not None:self.structs.register(clone)
            else:
                self.prepare(clone,mapping)
                self.functions.append(clone)
                if self.signatures is not None:self.signatures[symbol]=clone
            self.bound_checks.append((declaration,args,token,chain))
            if self.structs is not None:self.check_bounds()
        except CompileError as error:
            raise self.trace(error,chain) from None
        finally:self.current_chain=previous
        return clone

    def check_bounds(self):
        while self.bound_checks:
            declaration,args,token,chain=self.bound_checks.pop(0)
            for parameter,argument in zip(declaration.generic_params,args):
                if parameter.kind!='type':continue
                try:properties=self.structs.ensure(argument)
                except ValueError as error:raise self.trace(CompileError(token,str(error)),chain) from None
                if parameter.bound and not properties[parameter.bound]:
                    raise self.trace(CompileError(token,self.display(argument)+' is not '+parameter.bound),chain)

    def infer_arguments(self,declaration,actuals,result,token):
        params={p.token.text:p for p in declaration.generic_params};mapping={}
        def unify(pattern,actual):
            if actual is None:return
            if pattern in params:
                previous=mapping.get(pattern)
                if previous is not None and previous!=actual:
                    raise CompileError(token,'conflicting inference for '+pattern)
                mapping[pattern]=actual;return
            if is_array(pattern) and is_array(actual):
                pe,pn=pattern[1:-1].rsplit(';',1);ae,an=actual[1:-1].rsplit(';',1)
                unify(pe,ae);unify(pn,an);return
            pa=type_application(pattern)
            aa=self.type_keys.get(actual) or type_application(actual)
            if pa and aa and pa[0]==aa[0] and len(pa[1])==len(aa[1]):
                for p,a in zip(pa[1],aa[1]):unify(p,a)
        patterns=[t for _,t in (declaration.fields if isinstance(declaration,Struct) else declaration.params)]
        if len(patterns)!=len(actuals):raise CompileError(token,'wrong number of arguments')
        for pattern,actual in zip(patterns,actuals):unify(pattern,actual)
        result_pattern=declaration.name.text+'<'+','.join(params)+'>' if isinstance(declaration,Struct) else declaration.result_type
        unify(result_pattern,result)
        if any(p not in mapping for p in params):return None
        return [mapping[p] for p in params]
