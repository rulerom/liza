"""Versioned adapters for the existing experiments. Never discard raw results."""
STAGES = ('v0','v1','v2','v3','v4')
COVERAGE = {
    'v0': {'subjects':'ten fixed acyclic u8/i8 functions', 'obligations':40,
           'negative_controls':8, 'excludes':['memory','user calls','machine code']},
    'v1': {'subjects':'eight fixed array/control-flow functions; four u8 elements and symbolic u32 indices',
           'obligations':32, 'negative_controls':9, 'excludes':['arbitrary memory','loops','machine code']},
    'v2': {'subjects':'readonly-view search and sequential i32 sum with symbolic u32 length',
           'obligations':74, 'negative_controls':8,
           'excludes':['invalid input views','allocation','aliasing/mutation/freeing','arbitrary LLVM loops','machine code']},
    'v3': {'subjects':'concrete V0/V1 LLVM pairs; defined inputs; calibrated LLVM refinement',
           'actual_pairs':90, 'calibration_pairs':10,
           'excludes':['Semantic IR to LLVM proof','loops','interprocedural optimization','machine code']},
    'v4': {'subjects':'eleven selected whole programs in the abstract resource model',
           'positive_programs':11, 'analyzer_mutations':7, 'summary_controls':8,
           'excludes':['all source programs','all storage_contract fields','termination',
                       'readonly views','recursion','Vec','allocator','LLVM','machine code']},
}
V4_POSITIVE = {'safe','call','result_call','update','factory','cfg','loop','live_loop',
               'wrap','two_buffers','two_regions_safe'}
V4_MUTATIONS = {'lose_ok_payload','wrong_call_origin','lose_phi_dependency','conflate_regions',
                'forget_backedge_origins','lose_unresolved_result','bypass_region_guard'}
V4_SUMMARIES = {'summary_empty_direct','summary_missing_returns','summary_missing_ok',
               'summary_empty_constructed_ok','summary_wrong_variant','summary_wrong_parameter',
               'summary_hidden_factory_region','summary_wrong_payload_origin'}


def require(condition, message):
    if not condition: raise ValueError(message)


def unique(rows, keys, count):
    require(isinstance(rows,list) and len(rows)==count, 'incomplete row count')
    require(len({tuple(r[k] for k in keys) for r in rows})==count, 'duplicate rows')


def validate(stage, raw):
    """Gate the expected experiment matrix, not arbitrary program correctness."""
    try:
        if stage in {'v0','v1'}:
            rows=raw['results'];controls=raw['negative_controls']
            unique(rows,('subject','stage'),40 if stage=='v0' else 32)
            unique(controls,('mutation',),8 if stage=='v0' else 9)
            require(all(r['status']=='proved' for r in rows),'unproved positive obligation')
            require(all(r['status']=='counterexample' for r in controls),'missed negative control')
            require(raw['unsupported_control']['status']=='unknown','unsupported control not rejected')
            require(raw['success'] is True,'child reported failure')
        elif stage=='v2':
            unique(raw['proofs'],('function','stage'),8)
            obligations=[r for p in raw['proofs'] for r in p['results']]
            require(len(obligations)==74,'incomplete inductive obligations')
            for p in raw['proofs']:
                require(p['status']=='supported','unsupported loop model')
                require(len({r['obligation'] for r in p['results']})==len(p['results']), 'duplicate obligation')
            require(all(r['status']=='proved' for r in obligations),'unproved induction')
            unique(raw['negative_controls'],('mutation',),8)
            for c in raw['negative_controls']:
                require(c['detected'] is True and c['replay']['different'] is True and
                        c['replay']['actual']['kind']!='ReplayLimit','unconfirmed mutation')
                require(any(r['status']=='counterexample_to_obligation' for r in c['results']), 'missing failed obligation')
            require(raw['success'] is True,'child reported failure')
        elif stage=='v3':
            unique(raw['calibration'],('name',),10)
            require(sum(r['negative'] is True for r in raw['calibration'])==7,'incomplete trap calibration')
            require(all(r['status']==('counterexample' if r['negative'] else 'verified')
                        for r in raw['calibration']), 'unsuitable or incomplete calibration')
            unique(raw['actual'],('name',),90)
            require(all(r['status']=='verified' for r in raw['actual']), 'unverified LLVM pair')
            require(raw['status']=='verified' and raw['calibration_status']=='verified','V3 gate failed')
        elif stage=='v4':
            require(set(raw['positive_cases'])==V4_POSITIVE and len(raw['positive_cases'])==11,'incomplete V4 positives')
            require(set(raw['summary_controls'])==V4_SUMMARIES and len(raw['summary_controls'])==8,'incomplete summary controls')
            results=raw['results']
            require(set(results)==V4_POSITIVE|V4_MUTATIONS|V4_SUMMARIES,'unexpected V4 coverage')
            require(all(results[n]['status']=='verified_fragment' for n in V4_POSITIVE),'unverified resource program')
            for name in V4_MUTATIONS:
                r=results[name]
                require(r['status']=='model_violation' and r['mutated_analyzer_accepts'] is True and
                        bool(r['original_rejection']) and any(t.get('reproduced') is True for t in r['traces']),
                        'mutation lacks concrete replay')
            for name in V4_SUMMARIES:
                r=results[name]
                require(r['baseline_status']=='verified_fragment' and r['status']=='summary_failure' and
                        r['concrete_status']=='summary_failure' and bool(r['concrete_summary_failures']),
                        'understated summary lacks concrete confirmation')
        else: raise ValueError('unknown experiment')
    except (KeyError,TypeError,ValueError) as error:
        return {'status':'failed','reason':str(error)}
    return {'status':'passed','reason':'expected experiment matrix and controls passed; not a general correctness certificate'}


def observations(raw, stage):
    """An index into the untouched report, not a replacement interpretation."""
    result=[]
    def walk(value,path,role='subject'):
        if isinstance(value,dict):
            if stage=='v3' and value.get('negative') is True: role='negative_control'
            if 'status' in value and isinstance(value['status'],str):
                status=value['status']
                category={'proved':'proved_in_model','verified':'refinement_verified',
                          'verified_fragment':'fragment_verified','unknown':'unknown',
                          'unsuitable':'unsuitable','counterexample':'reported_counterexample',
                          'counterexample_to_obligation':'inconclusive_obligation_failure',
                          'summary_failure':'inconclusive_contract_failure',
                          'coverage_failure':'inconclusive_obligation_failure',
                          'guard_failure':'inconclusive_obligation_failure'}.get(status,'raw_status')
                if status=='model_violation':
                    category='confirmed_model_violation' if any(t.get('reproduced') is True for t in value.get('traces',[])) else 'inconclusive_model_violation'
                if status=='summary_failure' and value.get('concrete_status')=='summary_failure':
                    category='confirmed_return_contract_failure'
                result.append({'report_path':path,'raw_status':status,'category':category,'role':role})
            if value.get('replay',{}).get('different') is True and value['replay'].get('actual',{}).get('kind')!='ReplayLimit':
                result.append({'report_path':path+'/replay','category':'confirmed_model_violation','role':role})
            for key,child in value.items():
                child_role=role
                if key=='negative_controls' or key in V4_MUTATIONS: child_role='negative_control'
                if key=='unsupported_control': child_role='unsupported_control'
                if key in V4_SUMMARIES: child_role='summary_control'
                if stage=='v3' and key=='calibration': child_role='calibration'
                walk(child,path+'/'+key,child_role)
        elif isinstance(value,list):
            for i,child in enumerate(value):walk(child,path+'/'+str(i),role)
    walk(raw,'')
    return result
