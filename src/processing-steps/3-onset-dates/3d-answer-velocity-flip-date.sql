-- 3d: Velocity-flip date for answers.

UPDATE Posts a
JOIN (
    SELECT PostId,
           MIN(VoteDay) AS FlipDate
    FROM (
        SELECT v.PostId,
               DATE(v.CreationDate) AS VoteDay,
               SUM(CASE v.VoteTypeId WHEN 2 THEN 1 WHEN 3 THEN -1 ELSE 0 END) AS DailyNet
        FROM Votes v
        JOIN Posts p ON p.Id = v.PostId AND p.PostTypeId = 2
        WHERE v.VoteTypeId IN (2, 3)
          AND DATE(v.CreationDate) > DATE(p.hl_FirstAcceptanceDate)
        GROUP BY v.PostId, DATE(v.CreationDate)
    ) daily
    WHERE daily.DailyNet <= -2
    GROUP BY PostId
) flip ON flip.PostId = a.Id
SET a.hl_FirstVelocityFlipDate = flip.FlipDate
WHERE a.PostTypeId = 2;

-- todo: rename to hl_FirstVelocityFlipDateAfterAcceptance
