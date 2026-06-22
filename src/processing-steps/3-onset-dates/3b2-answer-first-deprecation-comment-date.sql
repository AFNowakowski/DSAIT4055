UPDATE Posts a
JOIN (
    SELECT c.PostId,
           MIN(c.CreationDate) AS FirstObsoleteCommentDate
    FROM Comments c
    JOIN Posts p ON p.Id = c.PostId AND p.PostTypeId = 2
    WHERE c.hl_IndicatedDeprecation = 1
    GROUP BY c.PostId
) oc ON oc.PostId = a.Id
SET a.hl_FirstObsoleteCommentDate = oc.FirstObsoleteCommentDate
WHERE a.PostTypeId = 2;
