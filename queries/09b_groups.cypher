// Answers: count active collaboration groups, the largest group, and groups with more than one person.
// Parameters: none.
// Shape: WCC assigns Active people to components; aggregate component sizes and summarize without treating isolated singleton people as meaningful groups.
CALL algo.WCC({nodeLabels:['Active'], relationshipTypes:['WORKS_WITH']}) YIELD node, componentId
WHERE coalesce(node.bot,false)=false
WITH componentId,count(DISTINCT node) AS groupSize
WITH collect({group:componentId,size:groupSize}) AS groupSizes
RETURN size(groupSizes) AS groups,
       reduce(largest=0,g IN groupSizes | CASE WHEN g.size>largest THEN g.size ELSE largest END) AS largestGroup,
       size([g IN groupSizes WHERE g.size>1]) AS nonSingletonGroups,
       groupSizes
