ALTER TABLE Posts
    ADD COLUMN IF NOT EXISTS hl_IsEphemeralBucket                                    TINYINT(1) NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptanceDate                                  DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerId                                INT        NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerCreationDate                      DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_OvertakeDate                                         DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstObsoleteCommentDate                             DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstBountyAfterAcceptanceDate                       DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstVelocityFlipDate                                DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerOvertakeDate                      DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerFirstObsoleteCommentDate          DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerFirstBountyAfterAcceptanceDate    DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerFirstVelocityFlipDate             DATETIME   NULL,
    ADD COLUMN IF NOT EXISTS hl_FirstAcceptedAnswerDeathDate                         DATETIME   NULL;
