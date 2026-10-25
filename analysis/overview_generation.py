"""Generate course overview only, from existing analysis results."""
from collections import Counter
from copy import deepcopy
import re

from .overview_contract import DISPLAY_LABELS, Overview, validate_overview
from .overview_prompt import OVERVIEW_INSTRUCTIONS

SLANG = {'에이쁠': 'A+', '에쁠': 'A+', '노베': '기초 지식이 없는 학생', '팀플': '팀 프로젝트'}
ADVICE = re.compile(r'검토해?\s*볼|살펴볼|점검해?\s*볼|유지하면|점검하면|검토하면|권장해요|추천해요')
STUDENT_CONDITION = re.compile(r'싫어|좋아하는|선호|성향|취향|초보|기초 지식|코딩 경험|배경지식|선수지식|학생에게|학생은|학생이라면')


def readable(text):
    for before, after in SLANG.items():
        text = text.replace(before, after)
    return text.replace('중간·기말', '중간고사와 기말고사').replace('·', ' 및 ').replace('/', ' 및 ')


def make_input(result, audience):
    """No original review text is sent to the overview model."""
    return {
        'audience': audience, 'category_labels': DISPLAY_LABELS,
        'summary_by_category': [{k: row[k] for k in ('category', 'mentioned', 'counts')}
                                for row in result['summary_by_category']],
        'overall_counts': dict(Counter(r['overall_sentiment'] for r in result['reviews'])),
        'reviews': [{'review_id': r['review_id'], 'items': [
            {k: readable(item[k]) if isinstance(item[k], str) else item[k]
             for k in ('category', 'sentiment', 'summary', 'condition')}
            for item in r['items']]} for r in result['reviews'] if r['status'] == 'ok'],
    }


def policy_findings(overview):
    findings = []
    for side in ('left', 'right'):
        for n, item in enumerate(overview[side]):
            location = f'{side}[{n}]'
            if f"{item['basis']}건" not in item['text']:
                findings.append({'location': location, 'issue': 'basis_not_in_sentence'})
            if overview['audience'] == 'instructor':
                if item['basis'] <= 2 and ADVICE.search(item['text']):
                    findings.append({'location': location, 'issue': 'small_sample_recommendation'})
                if side == 'right' and STUDENT_CONDITION.search(item['text']):
                    findings.append({'location': location, 'issue': 'student_condition_in_instructor_advice'})
            elif side == 'left' and not re.search(r'학생에게 맞아요[.!]?$', item['text'].strip()):
                findings.append({'location': location, 'issue': 'learner_recommendation_form'})
    suggestion = overview.get('suggestion') or ''
    sentences = [s for s in re.split(r'[.!?]+', suggestion) if s.strip()]
    if overview['audience'] == 'instructor' and (not 1 <= len(sentences) <= 2 or '볼 수 있어요' in suggestion):
        findings.append({'location': 'suggestion', 'issue': 'suggestion_length_or_repetition'})
    for category in overview['categories']:
        for n, group in enumerate(category['groups']):
            for field in ('short', 'detail'):
                if f"{group['basis']}건" not in group[field]:
                    findings.append({'location': f"{category['category']}.groups[{n}].{field}", 'issue': 'basis_not_in_sentence'})
    for text in all_prose(overview):
        if any(word in text for word in SLANG):
            findings.append({'location': 'prose', 'issue': 'slang_remaining'})
        if '{basis}' in text:
            findings.append({'location': 'prose', 'issue': 'unfilled_basis'})
    return findings


def all_prose(overview):
    for side in ('left', 'right'):
        yield from (item['text'] for item in overview[side])
    yield overview.get('suggestion') or ''
    for category in overview['categories']:
        yield from (s for s in category['headline'].values() if s)
        for group in category['groups']:
            yield group['topic']; yield group['short']; yield group['detail']


def finalize(raw, result, audience):
    """Compute IDs/basis first; replace count tokens only after verification."""
    overview, id_findings = validate_overview(raw, result, audience=audience)
    def counted(text, basis):
        text = readable(text).replace('{basis}', str(basis))
        # Models sometimes omit the token in a detailed sentence. Add only a
        # deterministic count from validated IDs, without changing its claim.
        if f'{basis}건' not in text:
            text = f'리뷰 {basis}건에서는 {text}'
        return text
    for side in ('left', 'right'):
        for item in overview[side]:
            item['text'] = counted(item['text'], item['basis'])
    overview['suggestion'] = readable(overview['suggestion']) if overview['suggestion'] else None
    for category in overview['categories']:
        category['headline'] = {k: readable(v) if v else None for k, v in category['headline'].items()}
        for group in category['groups']:
            group['topic'] = readable(group['topic'])
            for field in ('short', 'detail'):
                group[field] = counted(group[field], group['basis'])
    return overview, id_findings + policy_findings(overview)
