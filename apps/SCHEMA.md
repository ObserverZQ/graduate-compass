| table_name     | column_name                    | data_type                   | is_nullable |
| -------------- | ------------------------------ | --------------------------- | ----------- |
| programs       | id                             | uuid                        | NO          |
| programs       | name                           | text                        | NO          |
| programs       | degree_type                    | text                        | YES         |
| programs       | description                    | text                        | YES         |
| programs       | department                     | text                        | YES         |
| programs       | university                     | text                        | NO          |
| programs       | country                        | text                        | NO          |
| programs       | research_areas                 | text                        | YES         |
| programs       | duration_months                | integer                     | YES         |
| programs       | program_us_ranking             | integer                     | YES         |
| programs       | tuition_usd                    | integer                     | YES         |
| programs       | cost_of_living_usd             | integer                     | YES         |
| programs       | estimated_cohort_size          | integer                     | YES         |
| programs       | course_quality_score           | double precision            | YES         |
| programs       | workload_score                 | double precision            | YES         |
| programs       | job_placement_score            | double precision            | YES         |
| programs       | phd_score                      | double precision            | YES         |
| programs       | geographical_score             | double precision            | YES         |
| programs       | assistanship_score             | double precision            | YES         |
| programs       | living_experience              | text                        | YES         |
| programs       | climate                        | text                        | YES         |
| programs       | safety_score                   | double precision            | YES         |
| programs       | min_gpa                        | double precision            | YES         |
| programs       | min_toefl                      | integer                     | YES         |
| programs       | min_ielts                      | double precision            | YES         |
| programs       | additional_ad_requirement      | text                        | YES         |
| programs       | gre_required                   | boolean                     | YES         |
| programs       | acceptance_rate                | double precision            | YES         |
| programs       | official_website               | text                        | YES         |
| programs       | embedding                      | USER-DEFINED                | YES         |
| programs       | created_at                     | timestamp without time zone | YES         |
| programs       | school_id                      | uuid                        | YES         |
| saved_programs | id                             | uuid                        | NO          |
| saved_programs | user_profile_id                | uuid                        | YES         |
| saved_programs | program_id                     | uuid                        | YES         |
| saved_programs | notes                          | text                        | YES         |
| saved_programs | created_at                     | timestamp with time zone    | YES         |
| schools        | id                             | uuid                        | NO          |
| schools        | name                           | character varying           | NO          |
| schools        | country                        | character varying           | YES         |
| schools        | alpha_two_code                 | character                   | YES         |
| schools        | state_province                 | character varying           | YES         |
| schools        | city                           | character varying           | YES         |
| schools        | domains                        | text                        | YES         |
| schools        | web_pages                      | text                        | YES         |
| schools        | qs_world_rank                  | integer                     | YES         |
| schools        | the_world_rank                 | integer                     | YES         |
| schools        | usnews_global_rank             | integer                     | YES         |
| schools        | usnews_national_rank           | integer                     | YES         |
| schools        | search_vector                  | tsvector                    | YES         |
| schools        | created_at                     | timestamp with time zone    | YES         |
| test           | id                             | uuid                        | NO          |
| test           | name                           | character varying           | YES         |
| test           | created_at                     | timestamp with time zone    | NO          |
| user_profiles  | id                             | uuid                        | NO          |
| user_profiles  | name                           | text                        | YES         |
| user_profiles  | session_id                     | uuid                        | NO          |
| user_profiles  | user_id                        | uuid                        | YES         |
| user_profiles  | target_degrees                 | ARRAY                       | YES         |
| user_profiles  | resume_file_url                | text                        | YES         |
| user_profiles  | resume_raw_text                | text                        | YES         |
| user_profiles  | extracted_gpa                  | double precision            | YES         |
| user_profiles  | gpa_base                       | double precision            | YES         |
| user_profiles  | extracted_ranking              | text                        | YES         |
| user_profiles  | extracted_toefl                | double precision            | YES         |
| user_profiles  | extracted_toefl_legacy         | integer                     | YES         |
| user_profiles  | extracted_ielts                | double precision            | YES         |
| user_profiles  | extracted_work_experiences     | jsonb                       | YES         |
| user_profiles  | extracted_research_experiences | jsonb                       | YES         |
| user_profiles  | extracted_publications         | jsonb                       | YES         |
| user_profiles  | preferences                    | jsonb                       | YES         |
| user_profiles  | created_at                     | timestamp with time zone    | YES         |
| user_profiles  | updated_at                     | timestamp with time zone    | YES         |