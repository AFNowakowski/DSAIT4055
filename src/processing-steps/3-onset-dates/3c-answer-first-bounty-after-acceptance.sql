-- 3c: First bounty after acceptance, for first accepted answers.
--
-- For every first accepted answer (a Post referenced by a question's
-- hl_FirstAcceptedAnswerId), set hl_FirstBountyAfterAcceptanceDate to the date of
-- the first bounty announced on its parent question after the answer was accepted.

UPDATE Posts acc
    JOIN (SELECT q.hl_FirstAcceptedAnswerId AS AnswerId,
                 MIN(v.CreationDate)        AS FirstBountyDate
          FROM Posts q
                   JOIN Posts faa
                        ON faa.Id = q.hl_FirstAcceptedAnswerId
                   JOIN Votes v
                        ON v.PostId = q.Id
                            AND v.VoteTypeId = 8
                            AND v.CreationDate > faa.hl_FirstAcceptanceDate
          WHERE q.PostTypeId = 1
            AND q.hl_FirstAcceptedAnswerId IS NOT NULL
          GROUP BY q.hl_FirstAcceptedAnswerId) b ON b.AnswerId = acc.Id
SET acc.hl_FirstBountyAfterAcceptanceDate = b.FirstBountyDate;

