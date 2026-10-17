// Answers: whether an exact file path exists in the graph and whether it exists at HEAD.
// Parameters: $path is the exact File.path.
// Shape: retain historical files; return the HEAD flag without filtering out deleted files.
MATCH (f:File {path: $path})
RETURN f.path AS path, f.exists AS exists
