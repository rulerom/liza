import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.backend import llvm
from policy import decision, guided, acyclic
import json

class Policy(unittest.TestCase):
    def test_unrelated_large_frame_cannot_hide_growth(self):
        baseline={'text_bytes':1000,'frames':{'large':4096,'small':16}}
        candidate={'text_bytes':1100,'frames':{'large':4096,'small':512}}
        self.assertEqual(decision(baseline,candidate)['reasons'],['stack_growth:small'])

    def test_text_growth_rejected_at_budget(self):
        b={'text_bytes':1000,'frames':{}}
        self.assertTrue(decision(b,{'text_bytes':1250,'frames':{}})['accepted'])
        self.assertFalse(decision(b,{'text_bytes':1251,'frames':{}})['accepted'])

    def test_new_large_frame_rejected(self):
        self.assertFalse(decision({'text_bytes':1000,'frames':{}},{'text_bytes':1000,'frames':{'new':512}})['accepted'])

    def test_switch_backedge_excluded(self):
        blocks=[{'name':'a','terminator':{'op':'switch','args':['v','b',[0,'a']]}}, {'name':'b','terminator':{'op':'return','args':[]}}]
        self.assertFalse(acyclic(blocks))

    def test_names_do_not_affect_guidance_or_instructions(self):
        def select(name):
            source=f'fn {name}(x:u32)->u32 {{return x+1}} fn main()->u32 {{return {name}(3)}}'
            module=lower(Parser(source).parse());raw=llvm(module)
            changed,selected=guided(raw,json.loads(dump(module)))
            self.assertEqual(changed.replace(' inlinehint {',' {'),raw)
            return selected
        self.assertEqual(select('first'),['liza_first'])
        self.assertEqual(select('unrelated'),['liza_unrelated'])

    def test_recursive_function_excluded(self):
        module=lower(Parser('fn recur(x:u32)->u32 {if x==0 {return 0} return recur(x-1)} fn main()->u32 {return recur(4)}').parse())
        _,selected=guided(llvm(module),json.loads(dump(module)))
        self.assertNotIn('liza_recur',selected)

if __name__=='__main__':unittest.main()
