Choice	Value	Why
Chunk size	800 characters (≈150–200 tokens)	One paragraph is one idea in regulatory text. Precise retrieval, and a citation points to a specific passage
Overlap	100 characters (≈12%)	A sentence split across two chunks still appears whole in one of them. 10–20% is the usual range
Splitter	RecursiveCharacterTextSplitter	Splits on paragraphs first, then sentences, then words, so it respects the document’s structure instead of cutting mid-sentence
Metadata	source file + page number	Every red flag in the report can cite “EC FAQ, p. 7”. In compliance, a claim without a source is worthless
Embeddings	text-embedding-3-small (1536 dimensions)	Cheap, good quality, and multilingual, so it handles the Dutch DNB guidance too
Similarity	cosine	The standard for text embeddings: it compares meaning regardless of text length
Top-k	4	Enough to cover a question from several angles; more adds noise and cost