"""Bounded physical byte store, independent of the Semantic IR array model.

Objects are distinct successful stack allocations. Pointers have a concrete
origin and symbolic signed byte offset. No integer-to-pointer conversions,
heap, external pointers, address-space casts, or deallocation.
"""
from dataclasses import dataclass
import z3 as z
from .common import Unsupported


@dataclass(frozen=True)
class Pointer:
    origin:str
    offset:object


@dataclass(frozen=True)
class Object:
    alignment:int
    data:tuple
    initialized:tuple


class Memory:
    def __init__(self,objects=None):self.objects=dict(objects or {})
    def fork(self):return Memory(self.objects)
    def allocate(self,name,size,alignment):
        if name in self.objects:raise Unsupported('repeated allocation')
        if not 1<=size<=16 or alignment<1 or alignment&(alignment-1):raise Unsupported('allocation layout')
        self.objects[name]=Object(alignment,tuple(z.BitVecVal(0,8) for _ in range(size)),tuple(z.BoolVal(False) for _ in range(size)))
        return Pointer(name,z.IntVal(0))
    def object(self,pointer):
        if not isinstance(pointer,Pointer) or pointer.origin not in self.objects:raise Unsupported('unknown pointer origin')
        return self.objects[pointer.origin]
    def access(self,pointer,size,alignment):
        obj=self.object(pointer)
        if alignment<1 or alignment&(alignment-1):raise Unsupported('access alignment')
        if alignment>obj.alignment:raise Unsupported('alignment stronger than modeled allocation')
        return z.And(pointer.offset>=0,pointer.offset+size<=len(obj.data),pointer.offset%alignment==0)
    def load(self,pointer,size,alignment):
        obj=self.object(pointer);values=[];initialized=[]
        for k in range(size):
            byte=z.BitVecVal(0,8);valid=z.BoolVal(False)
            for j,(v,init) in enumerate(zip(obj.data,obj.initialized)):
                byte=z.If(pointer.offset+k==j,v,byte)
                valid=z.Or(valid,z.And(pointer.offset+k==j,init))
            values.append(byte);initialized.append(valid)
        return tuple(values),self.access(pointer,size,alignment),z.And(*initialized)
    def store(self,pointer,values,alignment):
        obj=self.object(pointer);data=list(obj.data);initialized=list(obj.initialized)
        for j in range(len(data)):
            for k,value in enumerate(values):
                condition=pointer.offset+k==j
                data[j]=z.If(condition,value,data[j])
                initialized[j]=z.Or(condition,initialized[j])
        valid=self.access(pointer,len(values),alignment)
        self.objects[pointer.origin]=Object(obj.alignment,tuple(data),tuple(initialized))
        return valid
    def gep(self,pointer,indices,scales,flags):
        if 'nuw' in flags and 'inbounds' not in flags:raise Unsupported('GEP nuw without inbounds')
        obj=self.object(pointer);offset=pointer.offset;valid=z.BoolVal(True)
        if 'inbounds' in flags:valid=z.And(valid,offset>=0,offset<=len(obj.data))
        for index,scale in zip(indices,scales):
            signed=z.BV2Int(index,is_signed=True);delta=signed*scale
            # V1 excludes address-index wrap even without LLVM no-wrap flags.
            valid=z.And(valid,delta>=-(1<<63),delta<(1<<63),offset+delta>=-(1<<63),offset+delta<(1<<63))
            if 'nuw' in flags:
                valid=z.And(valid,signed>=0,offset>=0,offset+delta<(1<<64))
            offset=offset+delta
            if 'inbounds' in flags:valid=z.And(valid,offset>=0,offset<=len(obj.data))
        return Pointer(pointer.origin,offset),valid
