create table public.competitor_stats (
  id serial not null,
  subzone character varying(255) not null,
  planning_area character varying(255) not null,
  venue_type character varying(255) not null,
  competitor_score numeric(5, 2) not null,
  competitor_density character varying(20) not null,
  created_at timestamp without time zone null default (now() AT TIME ZONE 'utc'::text),
  competitor_count integer null,
  underserved_score numeric(10, 2) null,
  overall_score numeric null,
  constraint competitor_stats_pkey primary key (id),
  constraint competitor_stats_subzone_venue_type_unique unique (subzone, venue_type)
) TABLESPACE pg_default;