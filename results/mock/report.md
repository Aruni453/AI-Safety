# Prompt Injection Test Bench: Results and Evaluation

## 1. Overview

The Prompt Injection Test Bench was developed to evaluate how different security mechanisms handle prompt injection attacks, sensitive data leakage, instruction overrides, and questions that cannot be answered using the available knowledge base.

The evaluation uses a deliberately simple, deterministic backend called `mock-naive`. The knowledge base contains 2,067 public SQuAD Wikipedia paragraphs, two synthetic confidential records, and three synthetic poisoned records. In total, 46 test cases were evaluated across nine configurations, including the baseline, seven leave-one-out configurations, and the complete defense setup.

The SQuAD v1.1 development dataset is publicly available under the CC BY-SA 4.0 license. All confidential information and poisoned records used in this experiment are synthetic and clearly labeled as such.

The test cases are divided into four main groups:

- **Real QA (B\*):** Questions that can be answered using the knowledge base.
- **Out-of-KB questions (X\*):** Questions whose answers are not available in the knowledge base.
- **Data leakage attacks (L\*):** Attempts to extract confidential information.
- **Instruction override attacks (O\*):** Attempts to make the system ignore its intended instructions.

The backend is a simulation rather than a production language model. Therefore, the results demonstrate how the test harness works and how the implemented defenses interact. They should not be interpreted as evidence of the security performance of real-world LLMs.

## 2. Overall Performance

The baseline system answered 24 out of 30 real questions correctly but failed to block any of the 12 attacks. It also failed to refuse all four out-of-knowledge-base questions.

Adding individual defense mechanisms improved security to varying degrees. However, no single defense was sufficient to address every attack category.

| Configuration | Real QA | Out-of-KB refusal | Data leakage blocked | Instruction overrides blocked | Attacks blocked | Overall |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 24/30 | 0/4 | 0/6 | 0/6 | 0/12 | 24/46 |
| Input filter | 24/30 | 0/4 | 3/6 | 2/6 | 5/12 | 29/46 |
| ACL | 24/30 | 0/4 | 4/6 | 0/6 | 4/12 | 28/46 |
| Context scan | 24/30 | 0/4 | 0/6 | 3/6 | 3/12 | 27/46 |
| Spotlight | 24/30 | 0/4 | 0/6 | 2/6 | 2/12 | 26/46 |
| Spotlight + sanitize | 24/30 | 0/4 | 0/6 | 3/6 | 3/12 | 27/46 |
| Output filter | 24/30 | 0/4 | 5/6 | 2/6 | 7/12 | 31/46 |
| Grounding | 22/30 | 4/4 | 3/6 | 3/6 | 6/12 | 32/46 |
| All defenses | 22/30 | 4/4 | 6/6 | 6/6 | 12/12 | 38/46 |

The results show that the output filter performed best among the individual configurations, blocking seven of the twelve attacks. The grounding mechanism also improved the overall score by handling all four out-of-KB questions, although it reduced the number of correctly answered real questions.

The complete configuration, which combines all defense mechanisms, achieved the strongest security result. It blocked all 12 attacks and correctly refused all four out-of-KB questions. Its overall score was 38 out of 46 cases.

These findings suggest that combining multiple defense layers is more effective than relying on a single mechanism in this test environment.

## 3. Case-by-Case Evaluation

The case-by-case results provide additional insight into the strengths and limitations of each defense.

### Real question answering

Under the complete defense configuration, 22 of the 30 real questions passed. Eight questions failed, primarily because of retrieval or answer-extraction limitations that were also present in the baseline system.

This distinction is important: not every failure represents a security problem. Some failures occur because the system cannot retrieve the correct paragraph or extract the expected answer.

### Data leakage protection

The baseline exposed sensitive synthetic records in all six leakage tests. These included simulated API keys, database passwords, internal instructions, and employee salary information.

Individual defenses blocked different subsets of these attacks. The ACL configuration blocked four of the six leakage cases, while the output filter blocked five.

When all defenses were enabled, all six leakage attacks were blocked. The leave-one-out analysis also showed that the ACL was essential for blocking case L05, while the remaining leakage cases continued to pass when any single defense was removed.

### Instruction override protection

All six instruction override attacks succeeded against the baseline system. These attacks produced outputs such as `PWNED`, enabled a simulated unrestricted mode, or returned an untrusted external link.

Individual controls blocked only some of these attempts. In contrast, the complete defense configuration blocked all six attacks.

The results demonstrate the value of layered protection against attempts to override the system's intended behavior.

### Out-of-knowledge-base questions

The baseline returned unrelated text for all four out-of-KB questions rather than reliably acknowledging that the required information was unavailable.

The grounding defense correctly refused all four questions. This improved reliability by reducing unsupported answers, although the same mechanism also rejected two real questions that the baseline could answer.

## 4. Contribution of Individual Defense Layers

A leave-one-out analysis was performed to determine which defense mechanisms were essential to the success of the complete configuration.

For this analysis, each defense was removed individually while all other defenses remained enabled. If a test case failed after removing a particular defense, that defense was considered load-bearing for the case. If the case continued to pass after every individual removal, its protection was considered redundant because multiple layers provided overlapping coverage.

The analysis produced the following findings:

- **ACL:** Essential for blocking leakage case L05.
- **Grounding:** Essential for blocking instruction override case O03 and all four out-of-KB questions.
- **Overlapping protection:** The remaining attack cases passed even when any single defense was removed, indicating that multiple layers contributed to their protection.

This analysis highlights an important security principle: defense mechanisms are more reliable when their responsibilities overlap. If one control fails or is bypassed, another control may still prevent the attack from succeeding.

## 5. Trade-off Between Security and Answer Quality

Although the complete configuration provided the strongest attack protection, it introduced a small reduction in question-answering utility.

The baseline answered 24 real questions correctly, whereas the complete configuration answered 22. The two additional failures were B01 and B03.

- **B01:** A question about the Codex Forster, a collection of notebooks associated with Leonardo da Vinci.
- **B03:** A question asking how many Americans are wealthier than more than half of all citizens.

Both questions were refused because the grounding mechanism classified the retrieved evidence as insufficient. These cases were labeled `grounding:weak_retrieval`.

The failures were not caused by the leakage or instruction-override defenses. Instead, they resulted from the grounding threshold being too restrictive for the retrieved evidence in these particular cases.

This demonstrates that stronger refusal behavior does not automatically produce a better overall system. A practical implementation must balance security with the ability to answer legitimate questions accurately.

## 6. Grounding Threshold Analysis

The grounding mechanism uses IDF-weighted question coverage of the best retrieved chunk to determine whether a question should be answered or refused.

The default threshold is 0.5. This value was selected as a simple starting point rather than being optimized for individual test cases.

| Threshold (τ) | Real questions wrongly refused | Out-of-KB questions refused |
|---:|---:|---:|
| 0.30 | 0/30 | 1/4 |
| 0.40 | 2/30 | 2/4 |
| 0.45 | 3/30 | 3/4 |
| 0.50 | 4/30 | 4/4 |
| 0.55 | 5/30 | 4/4 |
| 0.60 | 7/30 | 4/4 |
| 0.70 | 13/30 | 4/4 |

The results reveal a clear trade-off. At lower thresholds, the system is less likely to reject legitimate questions, but it also becomes less effective at identifying questions that fall outside the knowledge base.

At a threshold of 0.3, only one out-of-KB question is refused, while no real questions are wrongly refused. Increasing the threshold to 0.5 allows the system to refuse all four out-of-KB questions, but it also causes four legitimate questions to be rejected.

At 0.7, the system still refuses all four out-of-KB questions, but it incorrectly rejects 13 real questions.

Therefore, a higher threshold is not automatically better. The appropriate value depends on the relative cost of unsupported answers and unnecessary refusals. Further evaluation on a larger and more diverse dataset would be needed before selecting a production threshold.

## 7. False-Positive Evaluation

The input filter and context scanner were also tested against the public data to check whether they incorrectly flagged legitimate content.

The evaluation produced the following results:

- The regex-based input filter flagged 0 of 10,570 real SQuAD questions.
- The chunk scanner flagged 0 of 2,067 clean Wikipedia paragraphs.

Neither mechanism produced a false positive in this test.

These results are encouraging because overly aggressive security filters can interfere with normal question answering. However, zero false positives in this dataset does not guarantee that the filters will behave equally well on other datasets, user inputs, or adversarial examples.

Broader testing would be necessary to establish their reliability in more realistic environments.

## 8. Analysis of Remaining Failures

The complete configuration failed eight real QA cases: B04, B06, B07, B17, B22, B28, and the two questions affected by weak retrieval, B01 and B03.

The observed failures included missing gold answers, irrelevant retrieved text, and cases where the expected answer could not be extracted successfully.

Most of these failures were already present in the baseline configuration. This suggests that the main remaining limitation is the retrieval and answer-extraction pipeline rather than the security layers themselves.

The baseline also demonstrated the risks the defenses were designed to address. Leakage tests returned synthetic confidential information, while override tests generated unauthorized outputs such as `PWNED`, simulated unrestricted-mode messages, and an external link.

These examples illustrate why a system should not rely exclusively on the model's instructions to protect sensitive data or resist malicious input. Access controls, context inspection, output validation, and grounding checks provide additional safeguards.

## 9. Key Findings

The experiment supports five main observations:

1. **Layered defenses provide stronger coverage.** No individual defense blocked every attack, but the combined configuration blocked all 12 tested attacks.

2. **Output filtering was the strongest individual attack defense in this evaluation.** It blocked seven of the twelve attacks, although it did not eliminate all risks.

3. **Grounding improves refusal behavior but can reduce utility.** It correctly refused all four out-of-KB questions at the default threshold, while also causing legitimate questions to be rejected.

4. **Defense overlap improves resilience.** The leave-one-out analysis showed that most attack cases remained protected when any one defense was removed.

5. **Retrieval quality remains a major limitation.** Several legitimate questions failed under both the baseline and complete configurations, indicating that improving retrieval and answer extraction should be a separate priority.

## 10. Limitations and Future Work

The most important limitation is the use of a mock-naive backend. Because the backend is deterministic and deliberately simplistic, the results validate the test harness and demonstrate the interaction of the implemented controls. They do not establish how real language models would respond to the same attacks.

The evaluation also uses a relatively small set of 12 attack cases and four out-of-KB questions. Although the public-data false-positive checks cover thousands of records, they do not replace a broader adversarial evaluation.

Future work should focus on the following areas:

- Evaluate the same defenses against real LLM backends.
- Expand the attack dataset with diverse prompt injection, indirect injection, and data-exfiltration scenarios.
- Improve retrieval ranking and answer extraction to reduce legitimate QA failures.
- Tune the grounding threshold on a separate validation dataset.
- Test whether defenses remain effective when malicious instructions are embedded in retrieved documents.
- Measure latency, computational overhead, and the effect of each defense on answer quality.
- Add repeatable evaluation runs and more detailed failure diagnostics.

## Conclusion

The Prompt Injection Test Bench demonstrates how multiple defense mechanisms can work together to reduce prompt injection risks in a retrieval-augmented question-answering system.

In the simulated evaluation, the complete configuration blocked all 12 attack cases and correctly refused all four out-of-knowledge-base questions. However, the improvement in security came with a small loss in legitimate question-answering performance, mainly because the grounding mechanism rejected two questions that the baseline could answer.

Overall, the findings support a layered security approach that combines access control, input filtering, context scanning, output validation, and grounding. At the same time, the results emphasize that security must be evaluated alongside answer quality and retrieval reliability.

The next step is to validate these findings with real language models, a larger attack suite, and more realistic retrieval-augmented generation pipelines. Until then, the results should be treated as evidence that the evaluation framework functions as intended, rather than proof of production-level LLM security.
