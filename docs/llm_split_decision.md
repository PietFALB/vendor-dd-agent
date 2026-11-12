# The LLM is used where language and judgement are needed, and nowhere that the answer has to be exact. In your pipeline it does four things:

choose the searches (the ReAct agent),
read and weigh news articles (synthesis),
assess the overall risk (assessment),
write the summary and explanation (report).

Everything else is code. Why:

Facts have to be exactly right. Whether a company is on a sanctions list, what its LEI is, who its parent is: those are facts from registers. Code reads them back exactly; an LLM could misremember, rephrase or invent them. Your tests proved it: the LLM made up guidance pages and added amounts up to €1.45 billion.
Compliance needs the same answer every time. An LLM can give a different answer on the same input. Code gives exactly the same result every run. A sanctions check that’s “usually” right is useless.
Decisions have to be explainable. A compliance officer has to be able to tell a supervisor why a vendor was rejected. “Rule: EU listing means Do not onboard” is explainable. “The model thought so” isn’t.
What code can do, code does better. Fuzzy matching, calling an API, checking an amount: code does those faster, cheaper and testably. An LLM only adds value where text has to be understood or written.
Every LLM output needs a check. Each piece of LLM output is a place where something can go wrong, and each one needs its own check (URLs, names, amounts, sources). The less LLM, the fewer places to guard.

Where the LLM is strong, and why it’s used there:

News articles are unstructured text: whether an article really describes a risk takes understanding, not a regex.
Weighing several findings into one judgement is judgement work.
A readable summary is writing work.