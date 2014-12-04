--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- Data for Name: activity_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY activity_type (id, name, description) FROM stdin;
call	rpc call	A call to a registered rpc
register	register	Register an rpc so it can be called
publish	publish	Publish a message
subscribe	subscribe	Subscribe to a message
start	begin a session	Begin a new autobahn session
end	end a session	End an existing autobahn session
admin	Admin Domain	Rule over this space
\.


--
-- Data for Name: login; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY login (id, login, fullname, password, tzname, modified_by_user, modified_timestamp, salt, old_login, inactive) FROM stdin;
0	sys	System Admin	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
2	db	DB Admin	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
3	greg	Greg Fausak	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
4	adm	Public System Administrator	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
\.


--
-- Data for Name: session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY session (id, login_id, ab_session_id, tzname, created_by_user, created_timestamp, modified_by_user, modified_timestamp) FROM stdin;
\.


--
-- Data for Name: activity; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY activity (id, session_id, topic_name, type_id, allow, modified_by_user, modified_timestamp) FROM stdin;
\.


--
-- Name: activity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('activity_id_seq', 1, false);


--
-- Name: login_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('login_id_seq', 4, true);


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY role (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sysadmin	System Admin	0	2014-11-25 12:54:50.715127-06
2	public	Permissions granted to self	0	2014-12-03 17:06:00.894049-06
4	dbadmin	Database Administrator Access	0	2014-11-25 16:52:00.892507-06
5	dbuser	Database User Access	0	2014-11-25 17:13:51.684417-06
6	adm	Public System Administrator	0	2014-11-26 08:06:47.807554-06
\.


--
-- Data for Name: loginrole; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY loginrole (id, login_id, role_id, modified_by_user, modified_timestamp) FROM stdin;
1	0	1	0	2014-11-25 16:40:27.358583-06
2	0	2	0	2014-11-25 16:41:37.57475-06
8	2	2	0	2014-11-25 17:00:27.238068-06
9	2	4	0	2014-11-25 17:05:24.62864-06
10	3	2	0	2014-11-25 17:23:28.316645-06
11	3	5	0	2014-11-25 17:24:17.706538-06
12	4	2	0	2014-11-26 08:07:33.900107-06
13	4	6	0	2014-11-26 08:12:27.224807-06
\.


--
-- Name: loginrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('loginrole_id_seq', 13, true);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('role_id_seq', 6, true);


--
-- Name: session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('session_id_seq', 1, false);


--
-- Data for Name: sqlauth; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY sqlauth (component, version, profile) FROM stdin;
\.


--
-- Data for Name: topic; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY topic (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system, including authentication and authorization	0	2014-11-25 12:59:21.890086-06
2	sys.db	DB Administration	0	2014-11-25 17:06:40.391797-06
3	user.db	User DB Access	0	2014-11-25 17:15:03.700403-06
4	adm	Administrator Namespace	0	2014-11-26 08:06:09.931566-06
5	sys.topic.delete	Delete a topic	0	2014-12-03 19:58:36.862908-06
6	sys.topic.list	List topics	0	2014-12-03 19:58:55.580065-06
7	sys.topic.get	Get a topic	0	2014-12-03 19:59:44.461566-06
8	sys.topic.add	Add a topic	0	2014-12-03 20:07:45.035027-06
\.


--
-- Name: topic_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topic_id_seq', 8, true);


--
-- Data for Name: topicrole; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY topicrole (id, topic_id, role_id, type_id, allow, modified_by_user, modified_timestamp) FROM stdin;
1	1	1	call	t	0	2014-11-25 13:11:42.31319-06
2	1	1	register	t	0	2014-11-25 13:11:46.196604-06
3	1	1	publish	t	0	2014-11-25 13:11:58.806129-06
4	1	1	subscribe	t	0	2014-11-25 13:12:14.718075-06
5	1	1	admin	t	0	2014-11-25 13:12:29.087589-06
6	2	4	call	t	0	2014-11-25 17:08:48.530811-06
7	2	4	register	t	0	2014-11-25 17:09:28.036604-06
8	2	4	publish	t	0	2014-11-25 17:09:44.33833-06
9	2	4	subscribe	t	0	2014-11-25 17:09:51.953135-06
10	2	4	admin	t	0	2014-11-25 17:12:32.738286-06
11	3	5	call	t	0	2014-11-25 17:16:42.03835-06
12	3	5	subscribe	t	0	2014-11-25 17:17:39.320429-06
14	4	6	call	t	0	2014-11-26 08:21:46.422712-06
15	4	6	subscribe	t	0	2014-11-26 08:23:27.206593-06
16	5	2	call	t	0	2014-12-03 20:02:38.789938-06
17	6	2	call	t	0	2014-12-03 20:02:43.696013-06
18	7	2	call	t	0	2014-12-03 20:02:48.043339-06
19	8	2	call	t	0	2014-12-03 20:07:49.722207-06
\.


--
-- Name: topicrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topicrole_id_seq', 19, true);


--
-- Name: topicrole_role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topicrole_role_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

