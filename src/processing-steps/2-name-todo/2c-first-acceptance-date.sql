# -- ONLY FOR ANSWERS
# ALTER TABLE Posts
#     ADD COLUMN hl_FirstAcceptanceDate DATETIME NULL;
#
# UPDATE Posts p
# JOIN (
#     SELECT PostId, MIN(CreationDate) AS FirstAcceptance
#     FROM Votes
#     WHERE VoteTypeId = 1
#     GROUP BY PostId
# ) v ON v.PostId = p.Id
# SET p.hl_FirstAcceptanceDate = v.FirstAcceptance
# WHERE p.PostTypeId = 2;