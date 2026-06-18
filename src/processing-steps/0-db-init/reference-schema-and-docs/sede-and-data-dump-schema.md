**Markdown taken from [Database schema documentation for the public data dump and SEDE](https://meta.stackexchange.com/a/2678), 2025-09-30.**

**About this list:**  
-  **foreign key** fields are formatted as [links](https://data.stackexchange.com/stackoverflow/query/472607?table=posts) to their parent table  
- *italic* table names are found in **both** the Data Dump on [Archive.org](https://archive.org/download/stackexchange) as well as in the [SEDE](https://data.stackexchange.com/)  
- if a column is optional or nullable, when it is NULL, it won't appear as an attribute in data dump / `<row ...>`.

-----
## *Posts*  / PostsWithDeleted
You find in `Posts` all non-deleted posts. `PostsWithDeleted` includes rows with deleted posts while sharing the same columns with `Posts` but [for deleted posts only a few fields populated](https://meta.stackexchange.com/a/266431) which are marked with a <sup>1</sup> below. 

- `Id`<sup>1</sup> 
- `PostTypeId`<sup>1</sup> *(listed in the [`PostTypes`][4] table)*  
  <sub>1 = Question  
  2 = Answer  
  3 = Orphaned tag wiki  
  4 = Tag wiki excerpt  
  5 = Tag wiki  
  6 = Moderator nomination  
  7 = "Wiki placeholder" *(Appears to include auxiliary site content like the [help center introduction](https://stackoverflow.com/posts/58551602/body), [election description](https://stackoverflow.com/posts/8041931/body), and the tour page's [introduction](https://stackoverflow.com/posts/14264003/body), [ask](https://stackoverflow.com/posts/14264713/body), and [don't ask](https://stackoverflow.com/posts/14264412/body) sections)*  
  8 = Privilege wiki  
  9 = Article  
  10 = HelpArticle  
  12 = Collection  
  13 = ModeratorQuestionnaireResponse  
  14 = Announcement  
  15 = CollectiveDiscussion  
  17 = CollectiveCollection</sub>  

- [`AcceptedAnswerId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts) *(only present if `PostTypeId = 1`)*
- [`ParentId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts&pk=Id)<sup>1</sup> *(only present if `PostTypeId = 2`)*
- `CreationDate`<sup>1</sup>
- `DeletionDate`<sup>1</sup> *(only non-null for the SEDE `PostsWithDeleted` table. Deleted posts are not present on `Posts`. Column not present on data dump.)* 
- `Score`<sup>1</sup> *(generally non-zero for only Questions, Answers, and Moderator Nominations)*
- `ViewCount` *(nullable)*
- `Body` *([as rendered HTML](https://meta.stackexchange.com/questions/51177/include-markdown-post-bodies-in-the-data-dump), not Markdown)*
- [`OwnerUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users) *(only present if user has not been deleted; always -1 for tag wiki entries, i.e. the community user owns them)*
- `OwnerDisplayName` *(nullable)*
- [`LastEditorUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users) *(nullable)*
- `LastEditorDisplayName` *(nullable)*
- `LastEditDate` (e.g. `2009-03-05T22:28:34.823`) - *the date and time of the most recent edit to the post (nullable)*
- `LastActivityDate` (e.g. `2009-03-11T12:51:01.480`) - *datetime of the post's most recent activity*
- `Title` - *question title (`PostTypeId = 1`), or on Stack Overflow, the tag name for some tag wikis and excerpts (`PostTypeId = 4/5`)*
- `Tags`<sup>1</sup> - *question tags (`PostTypeId = 1`), or on Stack Overflow, the subject tag of some tag wikis and excerpts (`PostTypeId = 4/5`)*
- `AnswerCount` - *the number of undeleted answers (only present if `PostTypeId = 1`)*
- `CommentCount` *(nullable)*
- `FavoriteCount` *(nullable)*
- `ClosedDate`<sup>1</sup> *(present only if the post is closed)*
- `CommunityOwnedDate` *(present only if post is community wiki'd)*
- `ContentLicense`<sup>1</sup>

---
## *Users*
- `Id`
- `Reputation` 
- `CreationDate`
- `DisplayName`
- `LastAccessDate` *([Datetime user last loaded a page; updated every 30 min at most][5])*
- `WebsiteUrl`
- `Location`
- `AboutMe`
- `Views` *([Number of times the profile is viewed](https://meta.stackexchange.com/questions/311938/what-is-views-of-users-in-the-database-schema-documentation))*
- `UpVotes` *([How many upvotes the user has cast](https://meta.stackexchange.com/questions/260897/what-is-upvotes-of-users-in-database-schema-documentation))*
- `DownVotes`
- `ProfileImageUrl`
- `EmailHash` *(now always NULL, which means it won't appear as an attribute in the data dump XML)*
- `AccountId`  *(User's Stack Exchange Network profile ID); NULL if the user has hidden this community in their profile*

---
## *Comments*
- `Id`
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)
- `Score` 
- `Text` *(Comment body)*
- `CreationDate`
- `UserDisplayName`
- [`UserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users) *(Optional. Absent if user has been deleted)*  
- `ContentLicense`  

---
## *Badges*
- `Id`
- [`UserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)
- `Name` *(Name of the badge)*
- `Date` (e.g. `2008-09-15T08:55:03.923`)
- `Class`  
  <sub>1 = Gold  
  2 = Silver  
  3 = Bronze</sub>  

- `TagBased` = *`True` if badge is for a tag, otherwise it is a named badge*

---
## CloseAsOffTopicReasonTypes
- `Id`
- `IsUniversal`
- `InputTitle`
- `MarkdownInputGuidance` *shown while flagging/voting*
- `MarkdownPostOwnerGuidance` *shown when closed to OP*
- `MarkdownPublicGuidance` *shown when closed to priviledged users*
- `MarkdownConcensusDescription` (sic) *(nullable)* *shown above the public or post owner guidance*.
- `CreationDate`
- [`CreationModeratorId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)
- `ApprovalDate`
- `ApprovalModeratorId`
- `DeactivationDate`
- [`DeactivationModeratorId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)

---
## PendingFlags
Despite the name, this table in fact contains close-related flags and votes.

- `Id`
- `FlagTypeId` *(listed in the [`FlagTypes`][4] table)*  
  <sub>13 = canned flag for closure  
  14 = vote to close  
  15 = vote to reopen</sub>  

- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)
- `CreationDate`
- `CloseReasonTypeId` *(listed in the [`CloseReasonTypes`][4] table)*
- `CloseAsOffTopicReasonTypeId`, *if `CloseReasonTypeId = 102 (off-topic)` (listed in the [`CloseAsOffTopicReasonTypes`][4] table)*
- [`DuplicateOfQuestionId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts), *if `CloseReasonTypeId` is 1 or 101 (old duplicate or current duplicate)*
- `BelongsOnBaseHostAddress`, *for votes to close and migrate*

---
## PostFeedback 
Collects up and down votes from anonymous visitor and/or unregistered users. See [here](https://meta.stackexchange.com/a/194939/158100)  

- `Id`
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)
- `IsAnonymous`
- `VoteTypeId` *(listed in the [`VoteTypes`][4] table)*  
  <sub>2 = UpMod  
  3 = DownMod</sub>  

- `CreationDate`

---
## *PostHistory*  

*(Note that the history of deleted posts is scrubbed from this table in SEDE.)*

- `Id`  
- `PostHistoryTypeId` *(listed in the [`PostHistoryTypes`][4] table)*  
  <sub>1 = Initial Title - initial title *(questions only)*  
  2 = Initial Body - initial post raw body text  
  3 = Initial Tags - initial list of tags *(questions only)*  
  4 = Edit Title - modified title *(questions only)*  
  5 = Edit Body - modified post body (raw markdown)  
  6 = Edit Tags - modified list of tags *(questions only)*  
  7 = Rollback Title - reverted title  *(questions only)*  
  8 = Rollback Body - reverted body (raw markdown)  
  9 = Rollback Tags - reverted list of tags *(questions only)*  
  10 = Post Closed - post voted to be closed  
  11 = Post Reopened - post voted to be reopened  
  12 = Post Deleted - post voted to be removed  
  13 = Post Undeleted - post voted to be restored  
  14 = Post Locked - post locked by moderator  
  15 = Post Unlocked - post unlocked by moderator  
  16 = Community Owned - post now community owned  
  17 = Post Migrated - post migrated - *now replaced by 35/36 (away/here)*  
  18 = Question Merged - question merged with deleted question  
  19 = Question Protected - question was protected by a moderator.  
  20 = Question Unprotected - question was unprotected by a moderator.  
  21 = Post Disassociated - OwnerUserId removed from post by admin  
  22 = Question Unmerged - answers/votes restored to previously merged question	 
  24 = Suggested Edit Applied  
  25 = Post Tweeted  
  31 = Comment discussion moved to chat  
  33 = Post notice added - *`comment` contains foreign key to PostNotices*  
  34 = Post notice removed - *`comment` contains foreign key to PostNotices*  
  35 = Post migrated away - *replaces id 17*  
  36 = Post migrated here - *replaces id 17*  
  37 = Post merge source  
  38 = Post merge destination    
  50 = Bumped by Community User    
  52 = Question became hot network question (main) / Hot Meta question (meta)    
  53 = Question removed from hot network/meta questions by a moderator  
  66 = Created from Ask Wizard</sub>

 Additionally, in [older dumps][6] *(all guesses, all seem no longer present in the wild):*  
  <sub>23 = Unknown dev related event  
  26 = Vote nullification by dev *(ERM?)*  
  27 = Post unmigrated/hidden moderator migration?  
  28 = Unknown suggestion event  
  29 = Unknown moderator event *(possibly de-wikification?)*  
  30 = Unknown event *(too rare to guess)*</sub>  

- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  
- `RevisionGUID`: At times more than one type of history record can be recorded by a single action.  All of these will be grouped using the same RevisionGUID  
- `CreationDate` (e.g. `2009-03-05T22:28:34.823`)  
- [`UserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)
- `UserDisplayName`: populated if a user has been removed and no longer referenced by user Id; also happens to the author of a migrated post
- `Comment`: This field will contain the comment made by the user who edited a post.  
  - If PostHistoryTypeId = 10, this field contains the CloseReasonId of the close reason (listed in `CloseReasonTypes`):  
   <sub>***Old close reasons:***  
   1 = Exact Duplicate  
   2 = Off-topic  
   3 = Subjective and argumentative  
   4 = Not a real question  
   7 = Too localized  
   10 = General reference  
   20 = Noise or pointless (Meta sites only)  
   ***Current close reasons:***  
   101 = Duplicate  
   102 = Off-topic  
   103 = Unclear what you're asking  
   104 = Too broad  
   105 = Primarily opinion-based</sub>  

   - If `PostHistoryTypeId in (33,34)` this field contains the `PostNoticeId` of the `PostNotice`

- `Text`: A raw version of the new value for a given revision  
 <sub>- If `PostHistoryTypeId in (10,11,12,13,14,15,19,20,35)` this column will contain a JSON encoded string with all users who have voted for the `PostHistoryTypeId`</sub>  
 <sub>- If it is a duplicate close vote, the JSON string will contain an array of original questions as `OriginalQuestionIds`</sub>  
 <sub>- If `PostHistoryTypeId = 17` this column will contain migration details of either `from <url>` or `to <url>`</sub>    
- `ContentLicense`


---
## *PostLinks*  
- `Id` primary key  
- `CreationDate` when the link was created
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts) id of source post  
- [`RelatedPostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts) id of target/related post  
- `LinkTypeId`  type of link  
  <sub>1 = Linked (`PostId` contains a link to `RelatedPostId`)  
  3 = Duplicate (`PostId` is a duplicate of `RelatedPostId`)</sub>  

---
## RelatedQuestions
- `PostId`
- `RelatedPostId`
- `Position`
- `Score`

---
## PostNotices  
- `Id`  
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  
- [`PostNoticeTypeId`](https://data.stackexchange.com/stackoverflow/query/472607?table=postnoticetypes)  
  <sub>1 = Citation needed                 
2 = Current event                   
3 = Insufficient explanation        
10 = Current answers are outdated   
11 = Draw attention                 
12 = Improve details                
13 = Authoritative reference needed      
14 = Canonical answer required      
15 = Reward existing answer         
20 = Content dispute                
21 = Offtopic comments              
22 = Historical significance        
23 = Wiki Answer                    
24 = Policy Lock (SO Collectives)  
25 = Recommended Answer (SO Collectives)  
26 = Posted by Recognized Member/Admin (SO Collectives)  
27 = Endorsed Edit (SO Collectives)  
28 = Obsolete (SO Collectives)  
1000 = Redditted (SO)  
9001 = DMCA Takedown</sub> 
- `CreationDate`  
- `DeletionDate`  
- `ExpiryDate`  
- `Body`  *(when present contains the custom text shown with the notice)*  
- [`OwnerUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)  
- [`DeletionUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)  

---
## PostNoticeTypes  
- `Id`  
- `ClassId`  
  <sub>0 = DMCA or Redditted  
  1 = Historical lock  
  2 = Bounty  
  4 = Moderator notice (lock)</sub>  
- `Name`  
- `Body`  *(contains the default notice text)*  
- `IsHidden`  
- `Predefined`  
- `PostNoticeDurationId`  
  <sub>-1 = No duration specified  
  1 = 7 days (bounty)</sub>  

---
## PostTags  
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  
- [`TagId`](https://data.stackexchange.com/stackoverflow/query/472607?table=tags)

---
## ReviewRejectionReasons  
Canned rejection reasons for suggested edits. See [Show all review rejection reasons](https://data.stackexchange.com/stackoverflow/query/199800/show-all-review-rejection-reasons)  

- `Id`  
- `Name`  
- `Description`  
- `PostTypeId` (for reasons that apply to Wiki (5) or Excerpt (6) post types only, otherwise null)    

---
## ReviewTaskResults
- `Id`
- [`ReviewTaskId`](https://data.stackexchange.com/stackoverflow/query/472607?table=reviewtasks)
- `ReviewTaskResultTypeId` (listed in [`ReviewTaskResultTypes`][4])  
  <sub>1 = Skip   
  2 = Approve (suggested edits)  
  3 = Reject (suggested edits)  
  4 = Delete (low quality)  
  5 = Edit (first posts, late answers, low quality)  
  6 = Close (close, low quality)  
  7 = Looks OK (low quality)  
  8 = Do Not Close (close)  
  9 = Recommend Deletion (low quality answer)  
  10 = Recommend Close (low quality question)  
  11 = Other Action (first posts), previously "I'm Done"  
  12 = Reopen (reopen)  
  13 = Leave Closed (reopen)  
  14 = Edit and Reopen (reopen)  
  15 = Excellent (community evaluation)  
  16 = Satisfactory (community evaluation)  
  17 = Needs Improvement (community evaluation)  
  18 = No Action Needed (first posts, late answers)</sub>  

- `CreationDate` date only (`2018-07-31 00:00:00`); time data looks to be [purposefully removed to protect user privacy](/q/933)
- `RejectionReasonId` (for suggested edits; listed in `ReviewRejectionReasons`)
- `Comment`

---
## ReviewTasks
- `Id`
- `ReviewTaskTypeId` (listed in [`ReviewTaskTypes`][4])  
  <sub>1 = Suggested Edit  
  2 = Close Votes  
  3 = Low Quality Posts  
  4 = First Post  
  5 = Late Answer  
  6 = Reopen Vote  
  7 = Community Evaluation  
  8 = Link Validation  
  9 = Flagged Posts  
  10 = Triage  
  11 = Helper  
  12 = First Questions  
  13 = First Answers</sub>  

- `CreationDate` date only (`2018-07-31 00:00:00`)
- `DeletionDate` date only (`2018-07-31 00:00:00`)
- `ReviewTaskStateId` (listed in [`ReviewTaskStates`][7])  
  <sub>1 = Active  
  2 = Completed  
  3 = Invalidated</sub>

- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)
- [`SuggestedEditId`](https://data.stackexchange.com/stackoverflow/query/472607?table=suggestededits) (for suggested edits, which have their own numbering for historical reasons)
- [`CompletedByReviewTaskId`](https://data.stackexchange.com/stackoverflow/query/472607?table=ReviewTaskResults)  id associated to the ReviewTaskResult that stores the outcome of a completed review.

---
## SuggestedEdits  
If both approval and rejection date are null then this edit is still in review (and its corresponding entry in `ReviewTasks` will have an active state as well).

- `Id`
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  
- `CreationDate`
- `ApprovalDate` - NULL if not approved (yet).
- `RejectionDate` - NULL if not rejected (yet). 
- [`OwnerUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)  
- `Comment`
- `Text`
- `Title`
- `Tags`
- `RevisionGUID`

---
## SuggestedEditVotes
- `Id`
- [`SuggestedEditId`](https://data.stackexchange.com/stackoverflow/query/472607?table=suggestededits)  
- [`UserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)  
- `VoteTypeId` (listed in the [`VoteTypes`][4] table)  
  <sub>2 = Approve (technically UpMod)  
  3 = Reject (technically DownMod)</sub>  
- `CreationDate`
- [`TargetUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)
- `TargetRepChange`

---
## *Tags*  
- `Id`
- `TagName`
- `Count`
- [`ExcerptPostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  *(nullable) Id of Post that holds the excerpt text of the tag*
- [`WikiPostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts) *(nullable) Id of Post that holds the wiki text of the tag*
- `IsModeratorOnly`
- `IsRequired`

---
## TagSynonyms  
- `Id`  
- [`SourceTagName`](https://data.stackexchange.com/stackoverflow/query/472607?table=tags&pk=tagname)  *(nullable)*
- [`TargetTagName`](https://data.stackexchange.com/stackoverflow/query/472607?table=tags&pk=tagname)  *(nullable)*
- `CreationDate`
- [`OwnerUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)   *(nullable)*
- `AutoRenameCount`
- `LastAutoRename` *(nullable)*
- `Score`
- [`ApprovedByUserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users)  *(nullable)*
- `ApprovalDate` *(nullable)*

---
## *Votes*
- `Id`
- [`PostId`](https://data.stackexchange.com/stackoverflow/query/472607?table=posts)  
- `VoteTypeId` *(listed in the [`VoteTypes`][4] table - not all of these can actually appear in Data Explorer or the data dump, and some types - like the [reactions](https://stackoverflowteams.help/en/articles/8770232-reactions), 17 & 22-28 - are currently only implemented in Stack Overflow for Teams)*  
  <sub>-1 = InformModerator  
  0 = UndoMod  
  1 = AcceptedByOriginator  
  2 = UpMod *([AKA upvote](https://meta.stackexchange.com/a/157536))*  
  3 = DownMod *([AKA downvote](https://meta.stackexchange.com/a/157536))*  
  4 = Offensive  
  5 = Favorite *([AKA bookmark](https://meta.stackexchange.com/q/347558); `UserId` will also be populated)*  *feature removed after October 2022 / replaced [by Saves](https://meta.stackexchange.com/questions/382019)*  
  6 = Close (effective 2013-06-25: Close votes are **only** stored in table: `PostHistory`)  
  7 = Reopen  
  8 = BountyStart *(`UserId` and `BountyAmount` will also be populated)*  
  9 = BountyClose *(`BountyAmount` will also be populated)*  
  10 = Deletion  
  11 = Undeletion  
  12 = Spam  
  15 = ModeratorReview *(i.e., [a moderator looking at a flagged post](https://meta.stackexchange.com/a/157536))*  
  16 = ApproveEditSuggestion  
  17 = Reaction1 (Teams: celebrate)  
  18 = Helpful  
  19 = ThankYou *(see [Thank You reaction test](https://meta.stackoverflow.com/q/398367))*  
  20 = WellWritten  
  21 = Follow  
  22 = Reaction2 (Teams: smile)  
  23 = Reaction3 (Teams: mind blown)  
  24 = Reaction4 (Teams: clap)  
  25 = Reaction5 (Teams: heart)  
  26 = Reaction6 (Teams: fire)  
  27 = Reaction7 (Teams: trophy)  
  28 = Reaction8 (Teams: wave)  
  29 = Outdated *(see [Outdated Answers project](https://meta.stackoverflow.com/q/405302))*  
  30 = NotOutdated  
  31 = PreVote  
  32 = CollectiveDiscussionUpvote  
  33 = CollectiveDiscussionDownvote *([no longer used](https://meta.stackoverflow.com/q/429377))*  
  35 = privateAiAnswerCorrect *(see [Answer Bot experiment](https://meta.stackexchange.com/a/404813/134300))*  
  36 = privateAiAnswerIncorrect  
  37 = privateAiAnswerPartiallyCorrect</sub>  

- [`UserId`](https://data.stackexchange.com/stackoverflow/query/472607?table=users) *(present only if `VoteTypeId in (5,8)`; -1 if user is deleted)*  
- `CreationDate` Date only (`2018-07-31 00:00:00` *[time data is purposefully removed](https://meta.stackexchange.com/q/933/163250) to protect user privacy)*
- `BountyAmount` (present only if `VoteTypeId in (8,9)`)

---
## xxxTypes
*Not listed here:*  
- `xxxTypes` tables which list (Id, Name) pairs for `Posts.PostTypeId`, `Votes.VoteTypeId`, etc. See [Show all types][4] for an up-to-date list of all types.

---
## All Tables/Columns/Type

Find the exact [T-SQL datatype](https://docs.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql?view=sql-server-2017) and length/precision of each specific column in this query: 

[List all Fields in all Tables on SEDE](https://data.stackexchange.com/stackoverflow/query/835150/list-all-fields-in-all-tables-on-sede?/)


---
## Views / Stored Procedures

To support queries across multiple databases (aka sites) the following views and stored procedure exist in each database. See https://meta.stackexchange.com/questions/398985/ for usage scenarios.

---

## sede_databases

- `database_id`
- `database_name`
- `site_name`
- `tiny_name`
- `long_name`
- `site_type` *main_site or meta_site*
- `site_url`
- `sede_url`
- `api_site_parameter`
- `initialized` *Datetime when we started populating that database.*
- `made_available` *Datetime when the database came online and was ready for queries*
- `processing_time` *The duration between `initialized` and `made_available`, in `hh:mm:ss.fff` format*
- `questions` *Total number of questions in this site at the time of the current refresh*
- `answers` *Total number of answers in this site at the time of the current refresh*
- `latest_post` *The timestamp of the last _non-deleted_ post captured in this refresh*
- `notes` *This will be non-`NULL` when a database is in transition*

---
## sede_databases_markdown

-  `rn` *row number, for sorting by "long name"*
-  `content` *markdown with headers*

---
## sede_tables

- `database_id` *from `sys.databases`*
- `database_name` *from `sys.databases`* 
- `table_name` *from `sys.tables`*
- `latest_date` *The latest timestamp (e.g. `CreationDate`) for tables that have such a column.*
- `row_count` *Number of rows in the table, according to `sys.partitions`. **Note**: For `Posts`, this is `PostsWithDeleted`; if you want non-deleted total number of `Posts`, use `answers + questions` from `dbo.sede_databases`*
- `initialized` *Timestamp of initial table creation*
- `made_available` *Timestamp of final operation against table.*
- `processing_time` *Duration of `initialized` -> `made_available`, in `{hh:mm:ss.fff}` format.*

--- 
## sede_sites

- `site_name`
- `site_url`
- `database_name`
- `long_name`
- `site_id`

---
## sede_users

- `account_id`
- `site_id`
- `user_id`
- `reputation`
- `question_count`
- `answer_count`

---
## sede_ineachdb 

***note:** this is a stored procedure!*

See [this answer](https://meta.stackexchange.com/a/399304) for usage details.

|Parameter|Data Type|Default|Description|
|:--|:--|:--|:--|
|@SQLCommand          |nvarchar(4000)| |The SQL statement to run|
|@IncludeMainSites    |bit|1|Include all non-meta sites|
|@IncludeMetaSites    |bit|1|Include all meta sites|
|@IncludeMainMeta     |bit|1|Include `StackExchange.Meta`|
|@CollectResultsForMe |bit|1|For standard `SELECT` queries, this will attempt to put each database's results into a #temp table|
|@ErrorOnSkippedSites |bit|0|Set this to 1 if you want execution to halt in the event any site is missing due to transition change |

-----
Timestamps
=
All timestamps are [**`UTC`**][1], default format: `yyyy-MM-dd hh:mm:ss.fff` (stored with three digits of millisecond precision as implemented by SQL Server, making the "end" of a day `23:59:59.997`).  

**Example of conversion** current time to `PST` (including [DST][2]) using [`At Time Zone`][3]:  

<!-- language: lang-sql -->
    SELECT GetDate() At Time Zone 'UTC' At Time Zone 'Pacific Standard Time';

<sub>The time zones do not have great names, as they imply that you would have to use `'Pacific Daylight Time'` and know something about DST. To list **available time zones**: `SELECT * FROM sys.time_zone_info`</sub>


-----
ContentLicense
=
For tables with a `ContentLicense` column, the string value here indicates that the content is licensed under one of the following three Creative Commons versions, depending on when the content was submitted or last edited ([more details](https://meta.stackexchange.com/questions/347758/creative-commons-licensing-ui-and-data-updates)):

|ContentLicense Value|Date Start|Date End|Link|
|:--:|:--:|:--:|:--:|
|CC BY-SA 4.0|2018-05-02|-|[/licenses/by-sa/4.0/](https://creativecommons.org/licenses/by-sa/4.0/)|
|CC BY-SA 3.0|2011-04-08|2018-05-01|[/licenses/by-sa/3.0/](https://creativecommons.org/licenses/by-sa/3.0/)|
|CC BY-SA 2.5|-|2011-04-07|[/licenses/by-sa/2.5/](https://creativecommons.org/licenses/by-sa/2.5/)|

  [1]: https://www.epochconverter.com/
  [2]: https://www.google.com/search?q=dst
  [3]: https://docs.microsoft.com/sql/t-sql/queries/at-time-zone-transact-sql
  [4]: https://data.stackexchange.com/stackoverflow/query/36599/show-all-types
  [5]: https://meta.stackexchange.com/a/294750/230261
  [6]: https://meta.stackexchange.com/a/102644/230261
  [7]: https://data.stackexchange.com/stackoverflow/query/199801/show-all-review-task-states