-- answers only
ALTER TABLE Posts
    ADD COLUMN hl_OvertakeDate                   DATETIME NULL,
    ADD COLUMN hl_FirstObsoleteCommentDate       DATETIME NULL,
    ADD COLUMN hl_FirstBountyAfterAcceptanceDate DATETIME NULL,
    ADD COLUMN hl_FirstVelocityFlipDate          DATETIME NULL;

-- questions only
ALTER TABLE Posts
    ADD COLUMN hl_FirstAcceptedAnswerOvertakeDate                   DATETIME NULL,
    ADD COLUMN hl_FirstAcceptedAnswerFirstObsoleteCommentDate       DATETIME NULL,
    ADD COLUMN hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate DATETIME NULL,
    ADD COLUMN hl_FirstAcceptedAnswerFirstVelocityFlipDate          DATETIME NULL,
    ADD COLUMN hl_FirstAcceptedAnswerDeathDate                      DATETIME NULL;

-- yeah, I could have reused those columns, it's for ease of verification
