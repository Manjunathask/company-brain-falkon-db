// Answers: recompute whether each known File exists at the current Git HEAD.
// Parameters: $paths contains normalized paths present in HEAD.
// Shape: update all File nodes from one HEAD snapshot while retaining historical nodes.
MATCH (f:File)
SET f.exists = f.path IN $paths
RETURN count(f) AS filesChecked
