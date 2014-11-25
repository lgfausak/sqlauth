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

COPY login (id, login, fullname, password, tzname, modified_by_user, modified_timestamp) FROM stdin;
0	sys	System Admin	123test	America/Chicago	0	2014-11-25 16:39:11.141461-06
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

SELECT pg_catalog.setval('login_id_seq', 1, true);


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY role (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sysadmin	System Admin	0	2014-11-25 12:54:50.715127-06
2	self	Permissions granted to self	0	2014-11-25 12:54:54.368095-06
\.


--
-- Data for Name: loginrole; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY loginrole (id, login_id, role_id, modified_by_user, modified_timestamp) FROM stdin;
1	0	1	0	2014-11-25 16:40:27.358583-06
2	0	2	0	2014-11-25 16:41:37.57475-06
\.


--
-- Name: loginrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('loginrole_id_seq', 5, true);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('role_id_seq', 3, true);


--
-- Name: session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('session_id_seq', 1, false);


--
-- Data for Name: topic; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY topic (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system, including authentication and authorization	0	2014-11-25 12:59:21.890086-06
\.


--
-- Name: topic_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topic_id_seq', 1, true);


--
-- Data for Name: topicrole; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY topicrole (id, topic_id, role_id, type_id, allow, modified_by_user, modified_timestamp) FROM stdin;
1	1	1	call	t	0	2014-11-25 13:11:42.31319-06
2	1	1	register	t	0	2014-11-25 13:11:46.196604-06
3	1	1	publish	t	0	2014-11-25 13:11:58.806129-06
4	1	1	subscribe	t	0	2014-11-25 13:12:14.718075-06
5	1	1	admin	t	0	2014-11-25 13:12:29.087589-06
\.


--
-- Name: topicrole_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('topicrole_id_seq', 1, false);


--
-- PostgreSQL database dump complete
--

