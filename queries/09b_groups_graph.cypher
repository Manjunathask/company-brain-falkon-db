// Answers: show the largest active collaboration group and its internal WORKS_WITH edges.
// Parameters: none.
// Shape: compute WCC, collect each group's people, select the largest, then return its internal collaboration edges capped at 200.
CALL {
  CALL algo.WCC({nodeLabels:['Active'],relationshipTypes:['WORKS_WITH']}) YIELD node,componentId
  WHERE coalesce(node.bot,false)=false
  WITH componentId,collect(DISTINCT node) AS members
  WITH collect({id:componentId,members:members,size:size(members)}) AS groups
  UNWIND groups AS group
  WITH group ORDER BY group.size DESC LIMIT 1
  UNWIND group.members AS member
  RETURN group.members AS members,member AS person
}
MATCH (person)-[r:WORKS_WITH]-(other:Person:Active)
WHERE other IN members AND id(person)<id(other)
RETURN person AS n,r,other AS m LIMIT 200
