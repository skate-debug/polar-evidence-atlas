# Contributing / 参与贡献

Contributions are welcome, especially newly published polar literature,
corrections to evidence profiles, improved Chinese scientific terminology, and
links to open data. Please open an issue before making a large structural
change.

欢迎提交最新极地研究文献、证据档案勘误、中文科学术语修订以及开放数据链接。若计划进行较大的结构调整，请先创建 Issue 讨论。

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
