#!/usr/bin/env python3
"""E4 conservative, explicitly exploratory brand/history discordance audit."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def normalize(s): return re.sub(r'[^a-z0-9]','',str(s).casefold())


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path('outputs/jazz/personalwab_source'))
    ap.add_argument('--output',type=Path,default=Path('outputs/jazz/personalwab_contradictions.json'))
    args=ap.parse_args()
    profiles=json.loads((args.root/'user_profiles.json').read_text()); history={}
    sources={}
    for p in [args.root/'user_profiles.json',*sorted(args.root.glob('user_history_part_*.json'))]:
        sources[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
        if p.name.startswith('user_history'):
            part=json.loads(p.read_text())
            if history.keys() & part.keys(): raise ValueError('Duplicate users across shards')
            history.update(part)
    discordant=[]; covered=0; matched_reviews=0; matched_brands=0
    for user,entry in sorted(profiles.items()):
        prefs={normalize(b) for b in re.split(r'[,;]',entry['user_profile'].get('Brand Preference','')) if normalize(b)}
        by_brand=defaultdict(dict)
        for h in history.get(user,[]):
            if h.get('split')!='history': continue
            product=h.get('product_info',{}); review=h.get('review',{})
            brand=normalize(product.get('details',{}).get('Brand') or product.get('store',''))
            rating=review.get('rating'); asin=review.get('parent_asin') or product.get('parent_asin')
            if brand in prefs and isinstance(rating,(int,float)) and asin:
                by_brand[brand][asin]=rating
        covered+=bool(by_brand); matched_brands+=len(by_brand); matched_reviews+=sum(len(v) for v in by_brand.values())
        bad=[b for b,ratings in by_brand.items() if len(ratings)>=2 and max(ratings.values())<=2]
        if bad:
            discordant.append(dict(user_sha256=hashlib.sha256(user.encode()).hexdigest(),brands=bad,
                ratings={b:list(by_brand[b].values()) for b in bad}))
    report=dict(analysis='EXPLORATORY brand-preference/history discordance, not all semantic contradictions',
        n_users=len(profiles),n_history_users=len(history),users_with_matched_brand_history=covered,
        matched_brands=matched_brands,matched_reviews=matched_reviews,
        users_with_discordance=len(discordant),fraction=len(discordant)/len(profiles),
        evidence=discordant,source_sha256=sources,
        protocol='orchestration/personalwab_contradiction_protocol.md')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['evidence','source_sha256']},indent=2))


if __name__=='__main__': main()
