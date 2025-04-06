import polars as pl
from pathlib import Path
import src
#work on the ones where there are the most failures
# check distinct question id for the question to topic id.
query = """SELECT data, "explanationId"
FROM public."Resource"
WHERE "type" = 'VIDEO'
"""

dfr = src.exec_postgres_query(query)
current_dir = Path.cwd()

# 2. Create the full path for the output file
file_path = current_dir / "resources.parquet"
dfr.write_parquet(file_path)
url_values = dfr.select(pl.col("data").struct["url"] == "")
#print(url_values.unique())
dfr = dfr.with_columns(yt_link=pl.col("data").struct[0]).drop("data")
#print(dfr["yt_link"])
#print(dfr.null_count())

dfq = src.load_tables("question")
dfea = src.load_tables("exam")
dfex = src.load_tables("explanation")
dfc = src.load_tables("course")
#print(f"dfc cols: {dfc.columns}")
dft = src.load_tables("topic")
dfqtt = src.load_tables("questiontotopic")

dfc = dfc.select([
    pl.col("id").alias("courseId"),
    pl.col("name").alias("CourseName")
])

dfq = dfq.select([
    pl.col("id").alias("questionId"),
    pl.col("examId"),
    pl.col("courseId"),
    pl.col("stats")
])

dfea = dfea.select([
    pl.col("id").alias("examId"), 
    pl.col("courseId"), 
    pl.col("season"), 
    pl.col("year")
])
dft = dft.select([
    pl.col("id").alias("topicId"), 
    pl.col("name").alias("topicName"), 
    pl.col("courseId")
])
dfqtt = dfqtt.select([
    pl.col("questionId"), 
    pl.col("topicId")
])
dfex = dfex.select([
    pl.col("id").alias("explanationId"),
    pl.col("questionId")
])

# Step 2: Join dfq and dfe on 'questionId' and 'examId'
df_q_e = dfq.join(dfea, on=["examId", "courseId"], how="inner")

# Step 3: Join the result with dfqtt on 'questionId'
df_q_e_qtt = df_q_e.join(dfqtt, on="questionId", how="inner")

# Step 4: Join the result with dft on 'topicId' and 'courseId'
df_q_e_qtt_t = df_q_e_qtt.join(dft, on=["topicId", "courseId"], how="inner")

# Step 5: Join with dfex on 'questionId' to add explanationId
main_df = df_q_e_qtt_t.join(dfex, on="questionId", how="outer")

#Step 6: Join the main dataframe with the resources on the explanationId
final_df = main_df.join(dfr, on="explanationId", how = "full")

# Print the final DataFrame
#print(final_df)
#print(f"Final_df columns: {final_df.columns}")
#print(f"DF null column values: {final_df["yt_link"].null_count()}")
# Filter for rows where 'yt_link' is NULL
null_rows = final_df.filter(
    pl.col("yt_link").is_null()
)

# Print the rows with null values
#print(null_rows)

# Save the filtered rows to a Parquet file
current_dir = Path.cwd()
file_path = current_dir / "null_rows.parquet"
null_rows.write_parquet(file_path)

print(f"Null rows written to {file_path}")

#make into feature

#Filter for rows where 'yt_link' is null
df_missing_videos = final_df.filter(
    pl.col("yt_link").is_null()
)


# Group by 'topicId' and 'examId' to count missing videos
df_summary = (
    df_missing_videos
    .group_by("topicName")
    .agg([
        pl.count("questionId").alias("missing_videos_count")
    ])
)

"""# Join with the topic table to get topic names
df_result = df_summary.join(
    dft.select(["topicId", "name"]), 
    on="topicId", 
    how="left"
)"""

#Show the final result
#print(df_summary)
# Calculate the sum of missing_videos_count
total_missing_videos = df_summary["missing_videos_count"].sum()

# Print the total
#print(f"Total missing videos: {total_missing_videos}")

#connect missing videos to ones with the most missed questions
#print(dfq.columns)

#calculates average per question and the associated  topics
# Step 1: Extract stats data from dfq
dfq_stats = dfq.select([
    pl.col("questionId").alias("questionId"),
    pl.col("stats").struct["submissions"].alias("submissions"),
    pl.col("stats").struct["submissionsCorrect"].alias("submissionsCorrect")
])

# Calculate percentage correct
dfq_stats = dfq_stats.with_columns(
    (pl.col("submissionsCorrect") / pl.col("submissions") * 100).alias("percentage_correct")
)

# Step 2: Join stats with df_missing_videos
df_missing_videos = df_missing_videos.join(dfq_stats, on="questionId", how="left")
#print(df_missing_videos.shape)
df_missing_videos = df_missing_videos.join(dfc, on="courseId", how="left")
#print(df_missing_videos.shape)
# Step 3: Select the desired columns
df_question_level = df_missing_videos.select([
    pl.col("questionId"),
    pl.col("CourseName").alias("Course Name"),
    pl.col("topicName"),
    pl.col("percentage_correct").alias("Average Percent Correct"),
    pl.col("submissions").alias("Total Submissions"),
    pl.col("submissionsCorrect").alias("Correct Submissions")
])

# Step 4: Filter out rows where questionId and topicName are NULL/empty
df_question_level_cleaned = df_question_level.filter(
    ~(
        pl.col("questionId").is_null() |
        pl.col("topicName").is_null()
    )
)

# Step 5: Save the cleaned DataFrame to a Parquet file
cleaned_file_path = current_dir / "question_level_missing_videos_cleaned_with_course_name.parquet"
df_question_level_cleaned.write_parquet(cleaned_file_path)

# Step 6: Print a preview of the cleaned DataFrame and file path
#print(df_question_level_cleaned.head())
print(f"Cleaned data written to {cleaned_file_path}")



#does by calculating mean topic score
"""
# Step 1: Extract stats data from dfq
dfq_stats = dfq.select([
    pl.col("questionId").alias("questionId"),
    pl.col("stats").struct["submissions"].alias("submissions"),
    pl.col("stats").struct["submissionsCorrect"].alias("submissionsCorrect")
])

# Calculate percentage correct
dfq_stats = dfq_stats.with_columns(
    (pl.col("submissionsCorrect") / pl.col("submissions") * 100).alias("percentage_correct")
)

# Step 2: Join stats with df_missing_videos
df_missing_videos = df_missing_videos.join(dfq_stats, on="questionId", how="left")

# Step 3: Group by topicName to summarize stats
df_summary_stats = (
    df_missing_videos
    .group_by("topicName")
    .agg([
        pl.count("questionId").alias("missing_videos_count"),
        pl.mean("percentage_correct").alias("avg_percentage_correct"),
        pl.sum("submissions").alias("total_submissions"),
        pl.sum("submissionsCorrect").alias("total_correct_submissions")
    ])
)

# Show the result
print(df_summary_stats)

# Save the summary to a Parquet file
summary_file_path = current_dir / "missing_videos_summary.parquet"
df_summary_stats.write_parquet(summary_file_path)
print(f"Summary written to {summary_file_path}")

# Step 4: Calculate total missing videos for all topics
total_missing_videos = df_summary_stats["missing_videos_count"].sum()
print(f"Total missing videos: {total_missing_videos}")
"""

#previous work bad
"""
dfq = (
    dfq.join(dfex, left_on="id", right_on="questionId")
    .join(dfr, left_on="id_right", right_on="explanationId", how="left")
    .join(dfc, left_on="courseId", right_on="id")
    .join(dft, left_on="courseId", right_on="id", how="left")
    .with_columns(
        course_name=pl.col("abbreviation") + " " + pl.col("number_right").cast(str)
    )
)





#print(dfq)
#print(dfq.columns)
dfq = (
    dfq.group_by("course_name")
    .agg(
        #
        pl.col("yt_link").count().alias("question_videos"),
        pl.col("yt_link").is_null().sum().alias("missing_question_videos"),
        pl.col("id").count().alias("total_questions"),
    )
    .sort("missing_question_videos")
)
print(dfq)
dfq = dfq.with_columns(
    (100 * pl.col("missing_question_videos") / pl.col("total_questions")).alias(
        "missing_percent"
    )
)

total_missing_question_videos = dfq["missing_question_videos"].sum()
total_videos = dfq["question_videos"].sum()
total_questions = dfq["total_questions"].sum()
##print(total_missing_question_videos)
#print(total_videos)
#print(total_missing_question_videos / total_questions * 100)
#print(dfq)
#print(df_topic_exam)
pl.Config().set_tbl_rows(100)
# print(dfq)

dfq = (
    dfq.group_by("course_name")
    .agg(
        #
        pl.col("yt_link").count().alias("question_videos"),
        pl.col("yt_link").is_null().sum().alias("missing_question_videos"),
        pl.col("id").count().alias("total_questions"),
    )
    .sort("missing_question_videos")
)
"""