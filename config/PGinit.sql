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


COPY login (id, login, fullname, password, tzname, modified_by_user, modified_timestamp, salt, old_login, inactive) FROM stdin;
0	sys	System Internal Root	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
1	adm	Public System Administrator	17q8IJB2AO5dCvCcjJg/DHcP51dAHrULJUD9zoNZIbg=	America/Chicago	0	2014-12-03 20:21:15.442137-06	oihewuhweg98797325	\N	\N
\.

SELECT pg_catalog.setval('login_id_seq', 2, true);

COPY topic (id, name, description, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system, including authentication and authorization	0	2014-11-25 12:59:21.890086-06
2	sys.topic.delete	Delete a topic	0	2014-12-03 19:58:36.862908-06
3	sys.topic.list	List topics	0	2014-12-03 19:58:55.580065-06
4	sys.topic.get	Get a topic	0	2014-12-03 19:59:44.461566-06
5	sys.topic.add	Add a topic	0	2014-12-03 20:07:45.035027-06
200	adm	Administrator Space	0	2014-11-26 08:06:09.931566-06
300	com	Community Space	0	2014-11-26 08:06:09.931566-06
400	pub	Public Space	0	2014-11-26 08:06:09.931566-06
500	role	Role Binding Hierarchy	0	2014-11-26 08:06:09.931566-06
501	role.sys	Role sys Binding	0	2014-11-26 08:06:09.931566-06
502	role.adm	Role adm Binding	0	2014-11-26 08:06:09.931566-06
503	role.com	Role com Binding	0	2014-11-26 08:06:09.931566-06
504	role.public	Role Public Binding	0	2014-11-26 08:06:09.931566-06
\.

SELECT pg_catalog.setval('topic_id_seq', 600, true);

COPY role (id, name, description, bind_to, modified_by_user, modified_timestamp) FROM stdin;
1	sys	All things system	501	0	2014-11-25 12:54:50.715127-06
2	adm	Administration	502	0	2014-11-25 12:54:50.715127-06
3	com	Community	503	0	2014-11-25 12:54:50.715127-06
4	public	Public	504	0	2014-11-25 12:54:50.715127-06
\.

SELECT pg_catalog.setval('role_id_seq', 5, true);

COPY loginrole (id, login_id, role_id, modified_by_user, modified_timestamp) FROM stdin;
1	0	1	0	2014-11-25 16:40:27.358583-06
2	0	2	0	2014-11-25 16:41:37.57475-06
3	0	3	0	2014-11-25 16:41:37.57475-06
4	0	4	0	2014-11-25 16:41:37.57475-06
5	1	2	0	2014-11-25 17:00:27.238068-06
6	1	3	0	2014-11-25 17:05:24.62864-06
7	1	4	0	2014-11-25 17:23:28.316645-06
\.

SELECT pg_catalog.setval('loginrole_id_seq', 8, true);

COPY sqlauth (component, version, profile) FROM stdin;
\.

COPY topicrole (id, topic_id, role_id, type_id, allow, modified_by_user, modified_timestamp) FROM stdin;
1	1	1	call	t	0	2014-11-25 13:11:42.31319-06
2	1	1	register	t	0	2014-11-25 13:11:46.196604-06
3	1	1	publish	t	0	2014-11-25 13:11:58.806129-06
4	1	1	subscribe	t	0	2014-11-25 13:12:14.718075-06
5	1	1	admin	t	0	2014-11-25 13:12:29.087589-06
6	200	2	call	t	0	2014-11-25 13:11:42.31319-06
7	200	2	register	t	0	2014-11-25 13:11:46.196604-06
8	200	2	publish	t	0	2014-11-25 13:11:58.806129-06
9	200	2	subscribe	t	0	2014-11-25 13:12:14.718075-06
10	200	2	admin	t	0	2014-11-25 13:12:29.087589-06
11	300	3	call	t	0	2014-11-25 13:11:42.31319-06
12	300	3	register	t	0	2014-11-25 13:11:46.196604-06
13	300	3	publish	t	0	2014-11-25 13:11:58.806129-06
14	300	3	subscribe	t	0	2014-11-25 13:12:14.718075-06
15	300	3	admin	t	0	2014-11-25 13:12:29.087589-06
16	400	4	call	t	0	2014-11-25 13:11:42.31319-06
17	400	4	register	t	0	2014-11-25 13:11:46.196604-06
18	400	4	publish	t	0	2014-11-25 13:11:58.806129-06
19	400	4	subscribe	t	0	2014-11-25 13:12:14.718075-06
20	400	4	admin	t	0	2014-11-25 13:12:29.087589-06
21	2	4	call	t	0	2014-11-25 13:12:29.087589-06
22	3	4	call	t	0	2014-11-25 13:12:29.087589-06
23	4	4	call	t	0	2014-11-25 13:12:29.087589-06
24	5	4	call	t	0	2014-11-25 13:12:29.087589-06
25	500	1	admin	t	0	2014-11-25 13:12:29.087589-06
26	501	1	admin	t	0	2014-11-25 13:12:29.087589-06
27	502	2	admin	t	0	2014-11-25 13:12:29.087589-06
28	503	3	admin	t	0	2014-11-25 13:12:29.087589-06
29	504	4	admin	t	0	2014-11-25 13:12:29.087589-06
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

