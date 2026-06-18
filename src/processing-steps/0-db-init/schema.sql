CREATE TABLE Comments
(
    Id                      INT      NOT NULL,
    PostId                  INT      NOT NULL,
    Score                   INT      NOT NULL,
    Text                    TEXT     NOT NULL,
    CreationDate            DATETIME NOT NULL,
    UserDisplayName         VARCHAR(30) NULL,
    UserId                  INT NULL,
    hl_IndicatedDeprecation TINYINT(1) DEFAULT NULL -- NULL=not checked, TRUE/FALSE=result
    PRIMARY KEY (Id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE PostTags
(
    PostId INT NOT NULL,
    TagId  INT NOT NULL,
    PRIMARY KEY (PostId, TagId)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE Posts
(
    Id                    INT      NOT NULL,
    PostTypeId            TINYINT UNSIGNED NOT NULL,
    AcceptedAnswerId      INT NULL, -- not used!! There will be dangling values
    ParentId              INT NULL,
    CreationDate          DATETIME NOT NULL,
    DeletionDate          DATETIME NULL,
    Score                 INT      NOT NULL,
    ViewCount             INT NULL,
    Body                  TEXT NULL,
    OwnerUserId           INT NULL,
    OwnerDisplayName      VARCHAR(40) NULL,
    LastEditorUserId      INT NULL,
    LastEditorDisplayName VARCHAR(40) NULL,
    LastEditDate          DATETIME NULL,
    LastActivityDate      DATETIME NULL,
    Title                 VARCHAR(250) NULL,
    Tags                  VARCHAR(500) NULL,
    AnswerCount           INT NULL,
    CommentCount          INT NULL,
    FavoriteCount         INT NULL,
    ClosedDate            DATETIME NULL,
    CommunityOwnedDate    DATETIME NULL,
    hl_IsStableBucket     TINYINT(1) DEFAULT NULL -- null=idk TRUE=stable FALSE=ephemeral
    PRIMARY KEY (Id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


CREATE TABLE Tags
(
    Id                INT NOT NULL,
    TagName           VARCHAR(35) NULL,
    Count             INT NOT NULL,
    ExcerptPostId     INT NULL,
    WikiPostId        INT NULL,
    hl_IsStableBucket TINYINT(1) DEFAULT NULL -- null=idk TRUE=stable FALSE=ephemeral
    PRIMARY KEY (Id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE Votes
(
    Id           INT NOT NULL,
    PostId       INT NOT NULL,
    VoteTypeId   TINYINT UNSIGNED NOT NULL,
    UserId       INT NULL,
    CreationDate DATETIME NULL,
    BountyAmount INT NULL,
    PRIMARY KEY (Id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE Votes
    ADD CONSTRAINT Fk_Votes_Posts FOREIGN KEY (PostId)
        REFERENCES Posts (Id);

ALTER TABLE Comments
    ADD CONSTRAINT Fk_Comments_Posts FOREIGN KEY (PostId)
        REFERENCES Posts (Id);

ALTER TABLE PostTags
    ADD CONSTRAINT Fk_PostTags_Posts FOREIGN KEY (PostId)
        REFERENCES Posts (Id);

ALTER TABLE PostTags
    ADD CONSTRAINT Fk_PostTags_Tags FOREIGN KEY (TagId)
        REFERENCES Tags (Id);

ALTER TABLE Posts
    ADD CONSTRAINT Fk_Posts_ParentId FOREIGN KEY (ParentId)
        REFERENCES Posts (Id);

CREATE INDEX Idx_Posts_PostTypeId ON Posts (PostTypeId);
CREATE INDEX Idx_Votes_VoteTypeId ON Votes (VoteTypeId);