# Contributing / 参与贡献

Contributions are welcome, especially newly published polar literature,
South China Sea cold-seep research from the rolling ten-year window,
corrections to evidence profiles, improved Chinese scientific terminology, and
links to open data. Please open an issue before making a large structural
change.

欢迎提交最新极地研究文献、证据档案勘误、中文科学术语修订以及开放数据链接。若计划进行较大的结构调整，请先创建 Issue 讨论。

南海冷泉专题优先收录最近十年的微生物研究。请明确水深、距海底高度、沉积物深度与宿主组织，并分别记录采样介质、主题和站位。目录中的自动标签仅用于发现文献，不能替代原文核查。

The international comparison collection uses the same ten-year window and
prioritizes source-specific comparisons relevant to SCS microbial ecology.
Record the discussion purpose and distinguish direct habitat comparisons from
mechanistic or contextual systems. Reuse an existing source ID when the DOI is
already curated; a second collection must not create a duplicate paper or claim.

国际比较专题同样优先最近十年的微生物研究，应记录具体讨论用途，并区分直接生境
比较、机制先例及背景体系。已建档 DOI 须复用已有来源 ID，避免第二专题重复计数。

## Evidence requirements / 证据要求

1. Provide a DOI or another persistent identifier.
2. Describe the sampled location, period, material, and analytical methods.
3. Separate directly reported observations from genomic, statistical, or model
   inference.
4. Record a retrievable evidence locator such as a section, figure, table, or
   page.
5. State important limitations and claims for which the source should not be
   over-cited.
6. Paraphrase findings. Do not commit copyrighted article text or abstracts
   unless their license clearly permits redistribution.

提交时请提供 DOI 或其他永久标识符，并注明采样地点、时间、样品类型、分析方法、证据位置及主要局限。请区分实测结果与基因组、统计或模型推断，并以准确转述为主；除非许可证明确允许，不应提交受版权保护的论文原文或摘要。

## Validation / 本地核验

```bash
make translations
make all
make public-snapshot
make public-check
```

English source records remain canonical for citation. Chinese translations are
a terminology-normalized reading layer and should be reviewed by someone
familiar with the scientific domain.

SCS records use `collection=scs-cold-seeps`, an empty `poles` array, and explicit
region concept IDs. Choose `compartments`, `topics`, and `sites` from
`config/collections.json`. Keep first-online discovery dates separate from
version-of-record citation years, and identify preprints or corrected versions.

For the SCS queue, use `config/cold_seep_reviewed.json` for explicitly inspected
bilingual evidence packets and `config/cold_seep_review_decisions.json` for
unpromoted decisions. Run `scripts/curate_cold_seep_reviews.py` to materialize
them, then `scripts/update_cold_seep_candidates.py --reclassify`. Use the former
script's `--refresh` only to intentionally revise existing packet-derived
profiles. Retrieval scripts require a local source cache; public builds use the
abstract-free snapshots and do not perform editorial review.

Record abstract-only access honestly. For full-text excerpts, name the sections
actually read; do not imply the entire paper or supplements were checked.
Retain notice links and unresolved preprint versions in the review ledger.
The generated review CSV and Markdown queue include the next action for each
unpromoted record.

For international packets, edit `config/global_cold_seep_reviewed.json` and run
`scripts/curate_global_cold_seep_reviews.py`, then the standard checks above.
Set `existing_source_id` for shared sources. Use `--refresh` to deliberately
update generated international profiles while retaining unrelated evidence.
Export the profiles and APA references with `make global-cold-seep-report`.
Supply `--review-date YYYY-MM-DD` for newly inspected packets; existing dates
are preserved unless the packet explicitly updates `reviewed_at` after a new
evidence check.

南海冷泉证据包须同时填写准确的中英文提取内容，注明实际核查材料与证据位置。
仅阅读摘要时应明确标注；核查相关全文段落不代表已检查全部图表或补充材料。
未建档记录须保留处理原因和下一步工作，勘误及待核查的预印本版本也应可追溯。
