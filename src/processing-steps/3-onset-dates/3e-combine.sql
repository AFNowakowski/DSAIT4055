-- get death date
UPDATE Posts q
JOIN Posts a
    ON a.Id = q.hl_FirstAcceptedAnswerId
   AND a.PostTypeId = 2
SET q.hl_FirstAcceptedAnswerOvertakeDate                   = a.hl_OvertakeDate,
    q.hl_FirstAcceptedAnswerFirstObsoleteCommentDate       = a.hl_FirstObsoleteCommentDate,
    q.hl_FirstAcceptedAnswerFirstVelocityFlipDate          = a.hl_FirstVelocityFlipDate,
    q.hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate = a.hl_FirstBountyAfterAcceptanceDate,
    q.hl_FirstAcceptedAnswerDeathDate = NULLIF(
        LEAST(
            COALESCE(a.hl_OvertakeDate,                   '9999-12-31 23:59:59'),
            COALESCE(a.hl_FirstObsoleteCommentDate,       '9999-12-31 23:59:59'),
            COALESCE(a.hl_FirstVelocityFlipDate,          '9999-12-31 23:59:59'),
            COALESCE(a.hl_FirstBountyAfterAcceptanceDate, '9999-12-31 23:59:59')
        ),
        '9999-12-31 23:59:59'
    )
WHERE q.PostTypeId = 1;
