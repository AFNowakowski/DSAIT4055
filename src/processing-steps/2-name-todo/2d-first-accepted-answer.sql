ALTER TABLE Posts
ADD COLUMN hl_FirstAcceptedAnswerId INT NULL;

UPDATE Posts q
JOIN (
    SELECT ParentId, Id
    FROM (
        SELECT a.Id, a.ParentId,
               ROW_NUMBER() OVER (
                   PARTITION BY a.ParentId
                   ORDER BY a.hl_FirstAcceptanceDate ASC, a.Id ASC
               ) AS rn
        FROM Posts a
        WHERE a.PostTypeId = 2
          AND a.hl_FirstAcceptanceDate IS NOT NULL
    ) ranked
    WHERE rn = 1
) best ON best.ParentId = q.Id
SET q.hl_FirstAcceptedAnswerId = best.Id
WHERE q.PostTypeId = 1;

ALTER TABLE Posts
ADD COLUMN hl_FirstAcceptedAnswerCreationDate DATETIME NULL;

UPDATE Posts q
JOIN Posts a ON a.Id = q.hl_FirstAcceptedAnswerId
SET q.hl_FirstAcceptedAnswerCreationDate = a.CreationDate
WHERE q.PostTypeId = 1
  AND q.hl_FirstAcceptedAnswerId IS NOT NULL;