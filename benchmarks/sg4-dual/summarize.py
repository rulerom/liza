"""Summarize completed B2 runs; trial percentiles are not pooled."""
import argparse,json,statistics
from pathlib import Path

def median(values):
    values=[v for v in values if v is not None]
    return statistics.median(values) if values else None

def throughput(row):
    starts=[s['generator_phases'][1]['start_ns'] for s in row['streams']]
    ends=[s['generator_phases'][1]['end_ns'] for s in row['streams']]
    window=(max(ends)-min(starts))/1e9
    return sum(s['delivered_unique'] for s in row['streams'])/window

def summarize(report):
    if report['status']!='measured':raise ValueError('completed series required')
    capacity=[s for s in report['samples'] if s['scenario']=='capacity']
    if len(capacity)%2:raise ValueError('unpaired samples')
    groups={};paired={}
    for a,b in zip(capacity[::2],capacity[1::2]):
        if a['rates']!=b['rates'] or {a['variant'],b['variant']}!={'single','dual'}:raise ValueError('pair order')
        pair={a['variant']:a,b['variant']:b};key=tuple(a['rates'])
        paired.setdefault(key,[]).append({'delivered_throughput_ratio':throughput(pair['dual'])/throughput(pair['single']),
           'service_cpu_ratio':sum(pair['dual']['usage'][k] for k in ('user_s','system_s'))/sum(pair['single']['usage'][k] for k in ('user_s','system_s'))})
    for row in capacity:groups.setdefault((tuple(row['rates']),row['variant']),[]).append(row)
    rows=[]
    for (rates,variant),samples in groups.items():
        rows.append({'rates':rates,'variant':variant,'repeats':len(samples),
          'delivered_kcopies_s_median':median([throughput(s)/1000 for s in samples]),
          'service_cpu_s_median':median([s['usage']['user_s']+s['usage']['system_s'] for s in samples]),
          'consumer_cpu_s_median':median([sum(o['consumer_cpu_ns'] for o in s['owner_results'])/1e9 for s in samples]),
          'service_peak_rss_MiB_median':median([s['service_peak_rss_bytes']/1048576 for s in samples]),
          'generator_cpu_s_median':median([sum(v['generator_cpu_s'] for v in s['streams']) for s in samples]),
          'collector_cpu_s_median':median([sum(v['collector_cpu_s'] for v in s['streams']) for s in samples]),
          'kernel_full_buffer_deltas':[s['kernel_delta']['dropped due to full socket buffers'] if s['kernel_delta'] else None for s in samples],
          'streams':[{'stream':i,
              'coverage_offered_pct_median':median([s['streams'][i]['coverage_offered']*100 if s['streams'][i]['coverage_offered'] is not None else None for s in samples]),
              'coverage_offered_pct_min':min([s['streams'][i]['coverage_offered']*100 for s in samples if s['streams'][i]['coverage_offered'] is not None],default=None),
              'input_shortfall_median':median([s['streams'][i]['input_shortfall'] for s in samples]),
              'delivery_gap_from_local_success_median':median([s['streams'][i]['delivery_gap_from_local_success'] for s in samples]),
              'local_send_failures_total':sum(s['streams'][i]['failed_local_sends'] for s in samples),
              'p99_ms_median':median([s['streams'][i]['latency_upper_ms']['p99'] for s in samples]),
              'p99_ms_samples':[s['streams'][i]['latency_upper_ms']['p99'] for s in samples],
              'generator_max_gap_ms_samples':[s['streams'][i]['generator_max_interpacket_gap_ns']/1e6 if s['streams'][i]['generator_max_interpacket_gap_ns'] else None for s in samples]}
             for i in range(2)]})
    isolation=[]
    for sample in report['samples']:
        if sample['scenario']=='capacity':continue
        b=sample['streams'][1]
        isolation.append({'scenario':sample['scenario'],'group_results':[o['result'] for o in sample['owner_results']],
            'B_offered_after_A_destroy':b['offered_after_peer_destroy_packets'],
            'B_delivered_after_A_destroy':b['offered_after_peer_destroy_copies_observed'],
            'B_after_coverage':b['after_peer_destroy_coverage_offered'],
            'B_after_p99_ms':b['after_peer_destroy_latency_upper_ms']['p99']})
    return {'limits':'Medians of per-trial metrics; percentiles are not pooled. Same-host configuration comparison, not pure CPU scaling or hard QoS isolation.',
            'rows':rows,'pairs':[{'rates':rates,'pairs':values,'median_throughput_ratio':median([v['delivered_throughput_ratio'] for v in values]),'median_cpu_ratio':median([v['service_cpu_ratio'] for v in values])} for rates,values in paired.items()],
            'isolation':isolation}

def main():
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.write_text(json.dumps(summarize(json.loads(a.report.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
