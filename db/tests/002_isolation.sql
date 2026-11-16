-- Tests de la migration 002 : cloisonnement, lecture seule, numérotation, corbeille, journal, paiement.
-- À lancer avec le rôle propriétaire ; chaque cas s'exécute ensuite sous le rôle indiqué (`app`, `service`).
-- Rien n'est conservé : tout est annulé à la fin, même en cas de succès.
--   psql "$URL_PROPRIETAIRE" -v ON_ERROR_STOP=1 -f db/tests/002_isolation.sql
-- Un cas : (ordre, intitulé, rôle, utilisateur connecté, requête, résultat attendu ou code d'erreur PostgreSQL).
-- Codes attendus : 42501 = refusé par les droits ou la RLS, 23503 = lien invalide, 23505 = doublon.

begin;

create function pg_temp.tests_002() returns table (n integer, test text, resultat text)
language plpgsql as $f$
declare
  ua constant text := '00000000-0000-4000-8000-00000000000a';   -- utilisatrice A
  ub constant text := '00000000-0000-4000-8000-00000000000b';   -- utilisateur B
  c record; obtenu text; echecs integer := 0;
  ns integer[] := '{}'; tests text[] := '{}'; resultats text[] := '{}';
begin
  begin
    grant app, service to current_user with set true, inherit false;
    insert into public.utilisateurs (id, email) values (ua::uuid, 'a@test.sn'), (ub::uuid, 'b@test.sn');

    for c in
      select * from (values
      -- ---- le rôle app ne peut pas contourner la RLS
      (1, 'app et service : ni superutilisateur ni contournement de la RLS', 'proprio', '',
        $$select string_agg(rolname || ' ' || rolsuper || ' ' || rolbypassrls, ', ' order by rolname) from pg_roles where rolname in ('app','service')$$, 'app false false, service false false'),
      (2, 'app et service n''appartiennent à aucun groupe', 'proprio', '',
        $$select count(*)::text from pg_auth_members am join pg_roles r on r.oid = am.member where r.rolname in ('app','service')$$, '0'),
      (3, 'app et service ne possèdent aucune table', 'proprio', '',
        $$select count(*)::text from pg_class where relnamespace = 'public'::regnamespace and pg_get_userbyid(relowner) in ('app','service')$$, '0'),
      -- ---- A crée son entreprise et un dossier
      (4, 'A crée son entreprise', 'app', ua,
        $$insert into entreprises (id, nom) values ('00000000-0000-4000-8000-0000000000ea', 'Garage A') returning nom$$, 'Garage A'),
      (5, 'essai gratuit de 14 jours créé', 'app', ua,
        $$select plan || ' ' || (fin - debut) from abonnements$$, 'essai 14'),
      (6, 'A est propriétaire', 'app', ua, $$select role from membres$$, 'proprietaire'),
      (7, 'A crée un client', 'app', ua,
        $$insert into clients (id, entreprise_id, nom) values ('00000000-0000-4000-8000-0000000000ca', '00000000-0000-4000-8000-0000000000ea', 'Client A') returning nom$$, 'Client A'),
      (8, 'dossier sans numéro : numéroté 2026-001', 'app', ua,
        $$insert into dossiers (id, entreprise_id, date, client_id, client_nom) values ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000ea', '2026-03-01', '00000000-0000-4000-8000-0000000000ca', 'Client A') returning numero$$, '2026-001'),
      (9, 'lignes : quantité 1,5 et main d''œuvre sans quantité', 'app', ua,
        $$with x as (insert into lignes (dossier_id, entreprise_id, designation, qte, prix_unitaire) values
            ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000ea', 'Câble', 1.5, 333),
            ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000ea', 'Main d''œuvre', null, 25000) returning 1)
          select count(*)::text from x$$, '2'),
      (10, 'A enregistre un versement', 'app', ua,
        $$with x as (insert into versements (dossier_id, entreprise_id, montant) values ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000ea', 10000) returning 1) select count(*)::text from x$$, '1'),
      (11, 'total : 1,5 × 333 arrondi à 500, + 25 000 ; versé 10 000', 'app', ua,
        $$select total_ht_base::bigint || ' / ' || verse::bigint from dossier_totaux$$, '25500 / 10000'),
      -- ---- B ne voit rien et ne touche rien chez A
      (12, 'B crée son entreprise', 'app', ub,
        $$insert into entreprises (id, nom) values ('00000000-0000-4000-8000-0000000000eb', 'Garage B') returning nom$$, 'Garage B'),
      (13, 'B ne voit que son entreprise', 'app', ub, $$select string_agg(nom, ',') from entreprises$$, 'Garage B'),
      (14, 'B ne voit aucune donnée de A', 'app', ub,
        $$select ((select count(*) from clients) + (select count(*) from dossiers) + (select count(*) from lignes)
               + (select count(*) from versements) + (select count(*) from journal) + (select count(*) from dossier_totaux))::text$$, '0'),
      (15, 'B ne voit que son compte, son adhésion, son abonnement', 'app', ub,
        $$select (select count(*) from utilisateurs) || ' ' || (select count(*) from membres) || ' ' || (select count(*) from abonnements)$$, '1 1 1'),
      (16, 'B ne peut pas créer un client chez A', 'app', ub,
        $$insert into clients (entreprise_id, nom) values ('00000000-0000-4000-8000-0000000000ea', 'Intrus') returning nom$$, '42501'),
      (17, 'B ne peut pas ajouter une ligne chez A', 'app', ub,
        $$insert into lignes (dossier_id, entreprise_id, designation) values ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000ea', 'x') returning designation$$, '42501'),
      (18, 'B ne peut pas accrocher sa ligne au dossier de A', 'app', ub,
        $$insert into lignes (dossier_id, entreprise_id, designation) values ('00000000-0000-4000-8000-0000000000da', '00000000-0000-4000-8000-0000000000eb', 'x') returning designation$$, '23503'),
      (19, 'B ne peut pas rattacher son dossier au client de A', 'app', ub,
        $$insert into dossiers (entreprise_id, client_id, client_nom) values ('00000000-0000-4000-8000-0000000000eb', '00000000-0000-4000-8000-0000000000ca', 'x') returning numero$$, '23503'),
      (20, 'B ne peut pas modifier le dossier de A', 'app', ub,
        $$with x as (update dossiers set client_nom = 'Volé' where id = '00000000-0000-4000-8000-0000000000da' returning 1) select count(*)::text from x$$, '0'),
      (21, 'B ne peut pas effacer les lignes de A', 'app', ub,
        $$with x as (delete from lignes where dossier_id = '00000000-0000-4000-8000-0000000000da' returning 1) select count(*)::text from x$$, '0'),
      (22, 'B ne peut pas modifier l''entreprise de A', 'app', ub,
        $$with x as (update entreprises set nom = 'Volé' where id = '00000000-0000-4000-8000-0000000000ea' returning 1) select count(*)::text from x$$, '0'),
      (23, 'sans utilisateur connecté : rien n''est visible', 'app', '',
        $$select ((select count(*) from entreprises) + (select count(*) from dossiers) + (select count(*) from utilisateurs))::text$$, '0'),
      -- ---- ce que le site n'a pas le droit de faire, même pour A
      (24, 'pas de suppression définitive d''un dossier', 'app', ua,
        $$delete from dossiers where id = '00000000-0000-4000-8000-0000000000da' returning numero$$, '42501'),
      (25, 'le site ne peut pas créer un abonnement', 'app', ua,
        $$insert into abonnements (entreprise_id, plan, fin) values ('00000000-0000-4000-8000-0000000000ea', 'annuel', '2099-01-01') returning plan$$, '42501'),
      (26, 'le site ne peut pas s''ajouter à une autre entreprise', 'app', ua,
        $$insert into membres (entreprise_id, user_id) values ('00000000-0000-4000-8000-0000000000eb', '00000000-0000-4000-8000-00000000000a') returning role$$, '42501'),
      (27, 'le site ne peut pas activer un abonnement', 'app', ua, $$select activer_abonnement('x')::text$$, '42501'),
      (28, 'le site ne peut pas changer les tarifs', 'app', ua, $$update tarifs set montant = 1 returning plan$$, '42501'),
      (29, 'le site ne lit pas les rappels', 'app', ua, $$select count(*)::text from rappels$$, '42501'),
      (30, 'le site ne lit pas les compteurs', 'app', ua, $$select count(*)::text from compteurs_dossiers$$, '42501'),
      (31, 'le site ne peut pas changer l''auteur d''une entreprise', 'app', ua,
        $$update entreprises set cree_par = '00000000-0000-4000-8000-00000000000b' returning nom$$, '42501'),
      (32, 'le site ne peut pas antidater une entreprise', 'app', ua, $$update entreprises set cree_le = '2001-01-01' returning nom$$, '42501'),
      (33, 'le site ne peut pas changer l''identifiant d''un dossier', 'app', ua, $$update dossiers set id = gen_random_uuid() returning numero$$, '42501'),
      (34, 'le site ne peut pas déplacer un dossier vers une autre entreprise', 'app', ua,
        $$update dossiers set entreprise_id = '00000000-0000-4000-8000-0000000000eb' returning numero$$, '42501'),
      (35, 'le site ne peut pas désigner l''auteur d''une suppression', 'app', ua,
        $$update dossiers set supprime_par = '00000000-0000-4000-8000-00000000000b' returning numero$$, '42501'),
      (36, 'un numéro de dossier ne peut pas être vidé', 'app', ua, $$update dossiers set numero = '  ' returning numero$$, '23514'),
      (37, 'sans utilisateur connecté : aucune écriture', 'app', '',
        $$insert into clients (entreprise_id, nom) values ('00000000-0000-4000-8000-0000000000ea', 'Anonyme') returning nom$$, '42501'),
      (38, 'sans utilisateur connecté : aucune création d''entreprise', 'app', '', $$insert into entreprises (nom) values ('Anonyme') returning nom$$, '42501'),
      (39, 'tarifs en vigueur : 10 000 F par mois, 100 000 F par an', 'app', ua,
        $$select tarif_en_vigueur('mensuel') || ' ' || tarif_en_vigueur('annuel')$$, '10000 100000'),
      (40, 'un email donne toujours le même compte (majuscules, espaces)', 'app', '',
        $$select (utilisateur_par_email('  Nouveau@Exemple.SN ') = utilisateur_par_email('nouveau@exemple.sn'))::text$$, 'true'),
      (41, 'un membre doit être un utilisateur existant', 'proprio', '',
        $$insert into membres (entreprise_id, user_id) values ('00000000-0000-4000-8000-0000000000ea', gen_random_uuid()) returning role$$, '23503'),
      -- ---- numérotation
      (42, 'deuxième dossier : 2026-002', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-01', 'Client A') returning numero$$, '2026-002'),
      (43, 'numéro saisi à la main conservé', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-02', 'Client A', ' 2026-010 ') returning numero$$, '2026-010'),
      (44, 'la suite repart du numéro saisi : 2026-011', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-03', 'Client A') returning numero$$, '2026-011'),
      (45, 'numéro libre accepté', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-04', 'Client A', 'F-77') returning numero$$, 'F-77'),
      (46, 'doublon de numéro refusé', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-05', 'Client A', 'F-77') returning numero$$, '23505'),
      (47, 'nouvelle année : la numérotation repart à 001', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom) values ('00000000-0000-4000-8000-0000000000ea', '2027-01-05', 'Client A') returning numero$$, '2027-001'),
      (48, 'au-delà de 999 : numéro saisi 2027-999 gardé', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero) values ('00000000-0000-4000-8000-0000000000ea', '2027-01-06', 'Client A', '2027-999') returning numero$$, '2027-999'),
      (49, 'au-delà de 999 : le suivant est 2027-1000', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom) values ('00000000-0000-4000-8000-0000000000ea', '2027-01-07', 'Client A') returning numero$$, '2027-1000'),
      (50, 'un dossier ne peut pas naître dans la corbeille ni antidaté', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero, supprime_le, supprime_par, cree_le) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-07', 'Client A', 'T-1', '2020-01-01', '00000000-0000-4000-8000-00000000000b', '2001-01-01')
          returning (supprime_le is null and supprime_par is null and cree_le > now() - interval '1 hour')::text$$, 'true'),
      (51, 'B a sa propre numérotation', 'app', ub,
        $$insert into dossiers (entreprise_id, date, client_nom) values ('00000000-0000-4000-8000-0000000000eb', '2026-04-01', 'Client B') returning numero$$, '2026-001'),
      -- ---- corbeille et journal
      (52, 'mise à la corbeille : auteur enregistré', 'app', ua,
        $$update dossiers set supprime_le = '2000-01-01' where numero = 'F-77' returning (supprime_par = '00000000-0000-4000-8000-00000000000a' and supprime_le > now() - interval '1 hour')::text$$, 'true'),
      (53, 'le numéro d''un dossier à la corbeille est réutilisable', 'app', ua,
        $$insert into dossiers (entreprise_id, date, client_nom, numero) values ('00000000-0000-4000-8000-0000000000ea', '2026-04-06', 'Client A', 'F-77') returning numero$$, 'F-77'),
      (54, 'rétablir un dossier dont le numéro est repris : refusé', 'app', ua,
        $$update dossiers set supprime_le = null where numero = 'F-77' and supprime_le is not null returning numero$$, '23505'),
      (55, 'rétablir après avoir changé le numéro', 'app', ua,
        $$update dossiers set supprime_le = null, numero = 'F-77 bis' where numero = 'F-77' and supprime_le is not null returning (supprime_par is null)::text$$, 'true'),
      (56, 'A modifie son dossier', 'app', ua,
        $$with x as (update dossiers set client_nom = 'Client A modifié', km = 45000 where id = '00000000-0000-4000-8000-0000000000da' returning 1) select count(*)::text from x$$, '1'),
      (57, 'A efface une ligne', 'app', ua,
        $$with x as (delete from lignes where designation = 'Câble' returning 1) select count(*)::text from x$$, '1'),
      (58, 'journal : état d''avant la modification du dossier', 'app', ua,
        $$select avant ->> 'client_nom' from journal where ligne_id = '00000000-0000-4000-8000-0000000000da' and action = 'modification'$$, 'Client A'),
      (59, 'journal : ligne effacée récupérable', 'app', ua,
        $$select (avant ->> 'designation') || ' ' || (avant ->> 'qte') from journal where table_nom = 'lignes' and action = 'suppression'$$, 'Câble 1.50'),
      (60, 'journal : corbeille et restauration tracées avec leur auteur', 'app', ua,
        $$select string_agg(action, ',' order by id) from journal where action in ('corbeille','restauration') and user_id = '00000000-0000-4000-8000-00000000000a'$$, 'corbeille,restauration'),
      (61, 'le site ne peut pas écrire dans le journal', 'app', ua, $$delete from journal returning id::text$$, '42501'),
      -- ---- abonnement expiré : lecture seule
      (62, '(l''abonnement de A expire)', 'proprio', '',
        $$with x as (update abonnements set fin = current_date - 1 where entreprise_id = '00000000-0000-4000-8000-0000000000ea' returning 1) select count(*)::text from x$$, '1'),
      (63, 'expiré : A lit toujours ses dossiers (export Excel)', 'app', ua,
        $$select (select count(*) from dossiers) || ' dossiers, ' || (select count(*) from lignes) || ' ligne, ' || (select count(*) from clients) || ' client'$$, '10 dossiers, 1 ligne, 1 client'),
      (64, 'expiré : création refusée', 'app', ua,
        $$insert into clients (entreprise_id, nom) values ('00000000-0000-4000-8000-0000000000ea', 'Après expiration') returning nom$$, '42501'),
      (65, 'expiré : modification refusée', 'app', ua,
        $$with x as (update dossiers set km = 1 where id = '00000000-0000-4000-8000-0000000000da' returning 1) select count(*)::text from x$$, '0'),
      (66, 'expiré : suppression refusée', 'app', ua,
        $$with x as (delete from lignes returning 1) select count(*)::text from x$$, '0'),
      (67, 'expiré : paramètres de l''entreprise figés', 'app', ua,
        $$with x as (update entreprises set nom = 'x' returning 1) select count(*)::text from x$$, '0'),
      -- ---- paiement : activation par le rôle service, une seule fois
      (68, '(un paiement mensuel est en attente)', 'proprio', '',
        $$insert into paiements (entreprise_id, plan, montant, paydunya_token) values ('00000000-0000-4000-8000-0000000000ea', 'mensuel', tarif_en_vigueur('mensuel'), 'jeton-test') returning montant::text$$, '10000'),
      (69, 'service confirme le paiement', 'service', '', $$select coalesce(activer_abonnement('jeton-test')::text, 'fait')$$, ''),
      (70, 'service confirme une seconde fois', 'service', '', $$select coalesce(activer_abonnement('jeton-test')::text, 'fait')$$, ''),
      (71, 'un seul abonnement créé, pour un mois, au tarif payé', 'proprio', '',
        $$select count(*) || ' ' || bool_and(fin = (current_date + interval '1 month')::date) || ' ' || sum(montant) from abonnements where plan = 'mensuel'$$, '1 true 10000'),
      (72, '(second paiement, annuel, alors que le mois court encore)', 'proprio', '',
        $$insert into paiements (entreprise_id, plan, montant, paydunya_token) values ('00000000-0000-4000-8000-0000000000ea', 'annuel', tarif_en_vigueur('annuel'), 'jeton-test-2') returning montant::text$$, '100000'),
      (73, 'service confirme le second paiement', 'service', '', $$select coalesce(activer_abonnement('jeton-test-2')::text, 'fait')$$, ''),
      (74, 'prolongation : l''année part de la fin du mois en cours', 'proprio', '',
        $$select (debut = (current_date + interval '1 month')::date and fin = (current_date + interval '1 month' + interval '1 year')::date)::text from abonnements where plan = 'annuel'$$, 'true'),
      (75, 'abonnement payé : A écrit de nouveau', 'app', ua,
        $$insert into clients (entreprise_id, nom) values ('00000000-0000-4000-8000-0000000000ea', 'Après paiement') returning nom$$, 'Après paiement'),
      (76, 'service ne lit pas les dossiers', 'service', '', $$select count(*)::text from dossiers$$, '42501'),
      (77, 'service note un rappel envoyé', 'service', '',
        $$insert into rappels (abonnement_id, canal, jours_avant) values ('00000000-0000-4000-8000-0000000000ab', 'email', 3) returning canal$$, 'email'),
      (78, 'le même rappel ne part pas deux fois', 'service', '',
        $$insert into rappels (abonnement_id, canal, jours_avant) values ('00000000-0000-4000-8000-0000000000ab', 'email', 3) returning canal$$, '23505'),
      -- ---- suppression complète d'une entreprise (réservée au propriétaire de la base)
      (79, 'le propriétaire de la base supprime une entreprise', 'proprio', '',
        $$with x as (delete from entreprises where id = '00000000-0000-4000-8000-0000000000ea' returning 1) select count(*)::text from x$$, '1'),
      (80, 'ses données et son journal partent avec elle', 'proprio', '',
        $$select ((select count(*) from dossiers where entreprise_id = '00000000-0000-4000-8000-0000000000ea')
               + (select count(*) from journal where entreprise_id = '00000000-0000-4000-8000-0000000000ea'))::text$$, '0')
      ) as t (n, test, role, uid, sql, attendu) order by 1
    loop
      if c.test = 'service note un rappel envoyé' then   -- préparation : un abonnement d'identifiant connu pour les rappels
        insert into public.abonnements (id, entreprise_id, plan, fin)
          values ('00000000-0000-4000-8000-0000000000ab', '00000000-0000-4000-8000-0000000000eb', 'mensuel', current_date + 3);
      end if;
      if c.role = 'proprio' then reset role; else execute format('set local role %I', c.role); end if;
      perform set_config('app.user_id', c.uid, true);
      begin
        execute c.sql into obtenu;
      exception when others then
        obtenu := sqlstate;
      end;
      reset role;
      ns := ns || c.n; tests := tests || c.test;
      if obtenu is not distinct from c.attendu then
        resultats := resultats || 'ok'::text;
      else
        echecs := echecs + 1;
        resultats := resultats || format('ÉCHEC : attendu « %s », obtenu « %s »', c.attendu, coalesce(obtenu, 'rien'));
      end if;
    end loop;
    raise exception using errcode = 'T0000';   -- annule tout ce que les tests ont écrit
  exception when sqlstate 'T0000' then null;
  end;

  if echecs > 0 then
    raise exception '% test(s) en échec : %', echecs,
      (select string_agg(x.n || ' ' || x.t || ' -> ' || x.r, E'\n')
         from unnest(ns, tests, resultats) as x (n, t, r) where x.r <> 'ok');
  end if;
  return query select * from unnest(ns, tests, resultats);
end $f$;

select * from pg_temp.tests_002();

rollback;
