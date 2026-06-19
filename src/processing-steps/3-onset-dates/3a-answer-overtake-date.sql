UPDATE Posts acc
    JOIN (SELECT q.hl_FirstAcceptedAnswerId AS AnswerId,
                 MIN(v.CreationDate)        AS OvertakeDate
          FROM Posts q
                   JOIN Posts faa
                        ON faa.Id = q.hl_FirstAcceptedAnswerId
                   JOIN Posts other
                        ON other.ParentId = q.Id
                            AND other.PostTypeId = 2
                            AND other.Id <> q.hl_FirstAcceptedAnswerId
                   JOIN Votes v
                        ON v.PostId = other.Id
                            AND v.VoteTypeId = 1
                            AND v.CreationDate >= faa.hl_FirstAcceptanceDate
          WHERE q.PostTypeId = 1
            AND q.hl_FirstAcceptedAnswerId IS NOT NULL
          GROUP BY q.hl_FirstAcceptedAnswerId) ot ON ot.AnswerId = acc.Id
SET acc.hl_OvertakeDate = ot.OvertakeDate;
