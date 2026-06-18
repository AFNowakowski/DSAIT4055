-- IsStableBucket is already in the
ALTER TABLE Posts
    ADD COLUMN hl_IsEphemeralBucket TINYINT(1) NULL;

UPDATE Posts p
SET p.hl_IsStableBucket = TRUE
WHERE EXISTS (SELECT 1
              FROM PostTags pt
                       JOIN Tags t ON pt.tagId = t.id
              WHERE pt.postId = p.id
                AND t.hl_IsStableBucket = TRUE);

UPDATE Posts p
SET p.hl_IsEphemeralBucket = TRUE
WHERE EXISTS (SELECT 1
              FROM PostTags pt
                       JOIN Tags t ON pt.tagId = t.id
              WHERE pt.postId = p.id
                AND t.hl_IsStableBucket = FALSE);

UPDATE Posts
SET hl_IsEphemeralBucket = FALSE
WHERE hl_IsEphemeralBucket IS NULL
AND PostTypeId = '1';

UPDATE Posts
SET hl_IsStableBucket = FALSE
WHERE hl_IsStableBucket IS NULL
AND PostTypeId = '1';