CREATE  TABLE public.demographics_age_group (
  id bigint GENERATED BY DEFAULT AS IDENTITY NOT NULL,
  subzone text NULL,
  planning_area text NULL,
  "0-4" text NULL,
  "5-9" text NULL,
  "10-14" text NULL,
  "15-19" text NULL,
  "20-24" text NULL,
  "25-29" text NULL,
  "30-34" text NULL,
  "35-39" text NULL,
  "40-44" text NULL,
  "45-49" text NULL,
  "50-54" text NULL,
  "55-59" text NULL,
  "60-64" text NULL,
  "65-69" text NULL,
  "70-74" text NULL,
  "75-79" text NULL,
  "80-84" text NULL,
  "85_and_above" text NULL,
  all_age_groups text NULL,
  CONSTRAINT demographics_age_group_pkey PRIMARY KEY (id)
) TABLESPACE pg_default;