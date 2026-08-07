const asArray = (value) => (Array.isArray(value) ? value : []);

export function buildStudyGroups(plan, lastSession = null) {
  const due = asArray(plan?.revision_due);
  const dueConcepts = new Set(due.map((item) => item?.concept_id).filter(Boolean));

  const continueItems = lastSession && (lastSession.subject || lastSession.chapter)
    ? [{
        id: `continue:${lastSession.savedAt || 'latest'}`,
        kind: 'continue',
        eyebrow: 'Continue session',
        title: lastSession.chapter || `${lastSession.subject} practice`,
        subject: lastSession.subject || '',
        chapter: lastSession.chapter || '',
        mode: lastSession.mode || '',
        savedAt: lastSession.savedAt || null,
      }]
    : [];

  const recommendedItems = asArray(plan?.recommended_questions)
    .filter((item) => item?.question_id)
    .map((item) => ({
      id: `recommended:${item.question_id}`,
      kind: 'recommended',
      eyebrow: 'Recommended practice',
      title: item.chapter || item.question_id,
      questionId: item.question_id,
      subject: item.subject || '',
      chapter: item.chapter || '',
      difficulty: item.difficulty || '',
      reasons: asArray(item.reasons),
    }));

  const revisionItems = due
    .filter((item) => item?.concept_id)
    .map((item) => ({
      id: `revision:${item.concept_id}`,
      kind: 'revision',
      eyebrow: 'Revision due',
      title: item.concept_id,
      subject: item.subject || '',
      mastery: typeof item.p_known === 'number' ? item.p_known : null,
      nextReviewAt: item.next_review_at || '',
      reason: item.reason || '',
    }));

  const focusItems = asArray(plan?.weak_concepts)
    .filter((concept) => concept && !dueConcepts.has(concept))
    .map((concept) => ({
      id: `focus:${concept}`,
      kind: 'focus',
      eyebrow: 'Needs attention',
      title: concept,
      subject: '',
    }));

  return [
    { id: 'continue', label: 'Continue', items: continueItems },
    { id: 'recommended', label: 'Recommended', items: recommendedItems },
    { id: 'revision', label: 'Due for revision', items: revisionItems },
    { id: 'focus', label: 'Needs attention', items: focusItems },
  ];
}

export function filterStudyGroups(groups, subject) {
  if (!subject || subject === 'All') return groups;
  return groups.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.subject === subject),
  }));
}
