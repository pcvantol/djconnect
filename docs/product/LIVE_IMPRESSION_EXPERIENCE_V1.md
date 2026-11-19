# Live-impressie — één echte concertfoto met een verhaal van jouw DJ

**Assignment:** `DJC-LIVE-IMPRESSION-V1-20261108`  
**Eigenaarbesluit:** 8 november 2026.  
**Owning lane:** Core #1101; consumers Apple `pcvantol/djconnect-app#87` en VibeCast `pcvantol/djconnect-vibecast-receiver#10`.

## Actuele uitvoering — 19 november 2026

De eigenaar heeft integrale Core+Apple-uitvoering gevraagd met twee agents. De Mac-ontwikkelhost is in deze uitvoering vers geverifieerd (exit 0, MATCH, onboarding 4.5.13). Dit document legt het volledige ontwerp vast; code/contract/tests zijn in ontwikkeling op codex/core-live-impression-20261119. Review, CI, public-source/live-model/native acceptatie en installatie/deployment worden afzonderlijk vastgesteld.

## Historische intake, status en grens — 8 november 2026

Peter vraagt de eerder besproken Live-impressie-ontwerpen volledig uit te werken in lane-opdrachten, architectuur en repositorydocumentatie. Deze intake is de zelfstandige content-/media-opdracht; zij is **niet** de voice-adapteropdracht #1532, gewone artiestfoto v2, DJ Bulletin, Muziek aankondiging of Voor jou.

**Actuele bronstatus:** ontwerp en additive Core→Apple-contract in deze repository vastgelegd; lokale software-implementatie en regressies in uitvoering. De eerdere intake van 8 november selecteerde documentaire voorbereiding; de expliciete opdracht van 19 november selecteert integrale Core+Apple-implementatie. Geen nieuwe writer, providerabonnement, installatie of deployment wordt uit deze bronstatus afgeleid.

---

## 1. Propositie en publicatievoorwaarde

> **Een echte concertfoto waar jouw DJ een verhaal bij te vertellen heeft.**

Nieuw inhoudelijk DJMoment: **Live-impressie**. Een bijzonder historisch of recent daadwerkelijk uitgevoerd liveoptreden van een artiest die in de sessie speelt. Het visuele is primair; een persoonlijk verteld, brononderbouwd verhaal maakt het betekenisvol. Geen gewone biografie met willekeurige podiumfoto, livestream, concertagenda, tweede concertenapp of automatisch af te spelen liveopname.

Een eerste publicatie vereist samen:
1. Gevalideerde artiest-/eventrelatie en voldoende datum-/locatieprecisie.
2. Minimaal één echte, opgehaalde, decodeerbare en passende foto van **dat specifieke optreden**, met toegestane gebruiksbasis.
3. Een concreet, herleidbaar verhaal dat bij die avond hoort.
4. Geldige Session-/onderwerp-/doelgroep-/publicatiecontext en bestaande Planner-/Presence-toelating.

Geen nieuwe Live-impressie publiceren met een lege hero, albumcover, willekeurig portret, stockconcert of AI-reconstructie. Bij onvoldoende beeld of bewijs: binnen het begrensde onderzoek een ander optreden proberen, een andere geschikte bijdrage laten volgen of ruimte voor muziek laten. De rest van DJConnect blijft werken. Een fallback-only demo geldt niet als oplevering van dit type.

## 2. Wat de muziekrelatie wel en niet bewijst

De gewone aanleiding is de artiest die speelt; de huidige track mag een studio-opname zijn. Scheid drie betekenissen:
- Zelfde artiest, geen bewezen relatie tussen de huidige opname en het concert.
- Het lied is daar aantoonbaar uitgevoerd; dat bewijst niet dat je nu die opname hoort.
- De exacte spelende opname is aantoonbaar afkomstig van dat optreden.

Normale opening: ‘Nu we naar deze artiest luisteren: kijk eens naar dit optreden.’ Alleen met echte opnamebinding ‘dit is de uitvoering die je nu hoort’. Een foto bewijst ook niet automatisch het precieze nummer of moment binnen de set. Geen relatie afleiden uit alleen de string ‘live’, een artiestnaam, gelijke titel of albumcover.

Bij meerdere artiesten één bewuste bewezen hoofdartiest of de daadwerkelijk bewezen gezamenlijke context. Geen naamgenoot, tributeband, andere touravond of andere bezetting zonder correcte duiding.

## 3. Native productontwerp

Hergebruik bestaande Moment-/Flow-/historykaartbouwstenen en design system, met een **fotogerichte variant**. Geen nieuwe tab of apart scherm naast de bestaande productstructuur.

Visuele hiërarchie:
1. Kleine bestaande DJ-avatar als afzender + vast label **Live-impressie**. Geen rood LIVE-bolletje.
2. Grote hero over de bruikbare kaartbreedte; foto trekt de meeste aandacht.
3. Rustige zichtbare fotocredit; verplichte maker-/licentiegegevens niet uitsluitend verstoppen.
4. Artiest · zaal/festival/locatie · daadwerkelijke datum/jaar met eerlijke precisie.
5. Korte inhoudelijke verhaaltitel.
6. Twee à drie uitnodigende openingszinnen.
7. **Lees verder**, **Luister**, **Vraag hierover** en **Bronnen** via bestaande acties.

Foto aantikken opent de bestaande/gericht uitgebreide beeldviewer met groot beeld, zoom, bijschrift, credit en terugkeer naar dezelfde Flowpositie. Geen playback, microfoon, TTS of nieuwe research door navigatie.

**iPhone:** foto boven tekst, compacte inleiding, toegankelijke acties en Dynamic Type zonder vaste afgeknotte kaarthoogte. Behoud scrollpositie bij laden/openklappen/terugkeer. **iPad/Mac:** bij voldoende breedte beeld naast tekst, begrensde leesbreedte, keyboard/focusherstel. **VibeCast:** grote foto, datum/titel en korte opening; geen lange recensie of permanent chattranscript op tv.

Eén goede foto voldoet; optioneel maximaal twee extra beelden van hetzelfde optreden. Geen bijna identieke beelden om een carousel te vullen. Een galerij mag de eerste complete oplevering niet blokkeren. Geen auto-advance/Ken Burns-effect of zware Mood-filter. Houd het origineel zichtbaar; crop/afgeleiden alleen waar toegestaan en passend geduid. Geen generatief retoucheren, watermerkverwijdering of misleidende AI-upscale. Hero-kwaliteit op werkelijk native formaat beoordelen, niet overnemen van de bestaande kleine-artiestfotoondergrens.

Watch/widgets krijgen geen nieuwe galerij-/attachment-/sessiestartscope door deze opdracht. Bestaande toegelaten Momentdetailroutes mogen compatibel consumeren; ontbrekende ondersteuning is geen recht om private media naar passieve OS-opslag te kopiëren. Pi/ESP/API krijgen geen nieuwe writeropdracht; concrete regressies naar hun bestaande owners.

## 4. Narratie en vijf talen

Eén echte invalshoek: bijzondere locatie, doorbraak, reünie, samenwerking, podiumconcept of specifieke gebeurtenis. Richtlijn: 120–180 woorden totaal, met twee à drie openingszinnen; geen verplichte vulling. Inleiding is een deel van de geaccepteerde tekst. Titel, lead, body en bijschrift worden samen inhoudelijk beoordeeld.

Mood en Persona beïnvloeden taal, ritme en warmte, niet de feiten of bevoegdheden. Geen vaste genretekst, verzonnen herinnering/getuigenperspectief, ongefundeerd ‘legendarisch’, sentimentele invulling of claim dat de DJ de track zelf koos. Meningen van recensenten toeschrijven. Gevoelige verhalen niet geforceerd feestelijk maken. Bronfeiten beknopt in eigen woorden vertellen; geen volledige recensie of lange citaten overnemen.

**Tekst en opgeslagen Moment bestaan onafhankelijk van automatische spraak.** Autoplay volgt de geldige client-/outputinstelling. **Luister** is handmatige replay van dezelfde opgeslagen tekst, ook met autoplay uit, wanneer de normale spraakroute beschikbaar is. Providerfout: herstel/eerlijke unavailable-status, niet tekst verwijderen of handmatig luisteren van autoplay afhankelijk maken. Verlopen audio mag via de bestaande TTS-route opnieuw uit dezelfde tekst gemaakt worden; geen nieuw verhaal genereren.

Eén gekozen uitvoer spreekt, met bestaande audio-arbitrage en prioriteit voor expliciete interactie. Geen dubbele narratie op satelliet, telefoon en tv; geen tweede stemprovider of audioqueue.

Vijf talen NL/EN/DE/FR/ES voor type/copy/bijschriften/alttekst/a11y. Machinecodes en IDs niet vertalen. NL-copy: Live-impressie; Lees verder/Minder tonen; Bekijk foto; Foto 1 van 3; Luister/Stop; Vraag hierover; Bronnen; ‘De foto is tijdelijk niet beschikbaar.’

## 5. Echt onderzoek en beeldzoekwerk als normale route

**Brede internetsearch én imagesearch zijn essentieel**, geen optionele decoratie na een Wikipedia-template. Gebruik bestaande research-/searchinfrastructuur. Inventariseer actuele providers; voeg alleen ontbrekende adaptercapabilities toe, geen tweede onderzoeksengine.

Keten: geverifieerde artiest → enkele kandidaatoptredens → per optreden verhaal- en beeldbronnen ophalen → oorspronkelijke captions/galerijen en claims valideren → beste combinatie kiezen → bestaande narratie/review → publicatie.

Gebruik officiële artiest-/festival-/zaalarchieven, oorspronkelijke fotografen, interviews/omroepen, muziekpublicaties/concertverslagen, passende concert/setlistdata en open/gelicentieerde beeldarchieven. Een sterke primaire bron kan een eenvoudige gebeurtenis voldoende staven; betwiste/vergaande claims onafhankelijk corroboreren. Twee taalversies of gekopieerde persberichten zijn niet twee onafhankelijke bronnen.

Naam/aliassearch op een eerder geverifieerde artiest is toegestaan voor kandidaten. Een dedicated event-QID/MBID is niet verplicht als oorspronkelijke concert-/galerijbronnen de avond betrouwbaar identificeren. Deze eventresearchscope **verruimt niet stilzwijgend de bestaande v2-artistfoto- of Spotifyrechten**.

Candidate event heeft stabiele interne identiteit, optionele externe IDs, artiest, lokale concertdatum + precisie, locatie/stad, festival/tour/podium indien bewezen, bronverwijzingen en bewijs dat het optreden plaatsvond. Artikelpublicatie-, update- en retrievaltijd zijn geen concertdatum. Toekomstig/afgelast optreden wordt geen recent concertverslag.

Een afbeelding vereist oorspronkelijke asset-/fotopagina, bronrevisie/contentidentiteit, maker/bijschrift en herleidbare binding aan dát event. Alleen zoekranking, thumbnail, alttekst, EXIF of ‘artiest op podium’ volstaan niet. Een review kan foto's uit verschillende jaren bevatten; per foto controleren. Beeldanalyse mag kwaliteit/compositie helpen beoordelen, niet personen via gezicht herkennen of de gebeurtenis uit pixels bewijzen.

Kandidaatproviders, **geen reeds gekozen/geconfigureerde dependency**:
- Bestaande web/imagesearch; bijvoorbeeld Brave voor discovery met bronpagina én originele afbeeldingsverwijzing.
- Commons/Openverse voor beeldkandidaten en metadata; oorspronkelijke gebruiksbasis blijft te controleren.
- setlist.fm voor eventkandidaten via artiest-ID/datum/zaal waar toegestaan; setlist is geen opnamebewijs.
- Betaalde redactionele beeldbanken alleen na afzonderlijk passend besluit; geen automatische abonnementen/kosten.

Zoek alleen op benodigde publieke artiest-/eventdata. Geen Music DNA, privégeschiedenis, HA-hostnamen, ownerdetails, tokens of raw chat naar searchproviders. Geen paywall/login/CAPTCHA-omzeiling.

## 6. Eén Core-keten en gerichte contractdelta

```text
Bestaande playback/Plannergelegenheid of expliciete Ask DJ-vraag
→ bestaande actor/Profile/Sessioncontext
→ bestaande Knowledge/research-eigenaar met eventkandidaten
→ bestaande bronadapters: web + image search + oorspronkelijke pagina's
→ event-/beeld-/feiten-/gebruiksvalidatie
→ bestaande narratie/review, bevestigd Mood/Persona
→ laatste geldigheidscontrole + bestaande Planner/Presence
→ één immutable DJMoment + bestaande Sessionopslag
→ bestaande private/shared projecties en beheerde media
→ Apple / VibeCast / andere toegelaten consumer
```

Geen nieuwe Planner, Session, conversation engine, permanente researchdienst, fotoarchiefdienst, eigen clientsearch of playbackroute. Core bezit inhoud; clients bezitten presentatie. Expliciet Ask DJ-onderzoek hergebruikt dezelfde diensten, maar publiceert niet extra een proactief Moment voor dezelfde vraag.

Nieuwe semantische discriminatie is een echte inhoudsfamilie/type/subtype op de correcte plek in het bestaande model, niet alleen een UI-kop. Exact wiretype/capabilityversie bij implementatie vaststellen; onderstaande veldrollen zijn ontwerp, geen bestaand endpoint:
- Bestaande Session/Moment/entry-ID, publicationrevision en event-ID.
- Oorspronkelijke trigger-/artist-/recordingcontext met de juiste relatie en bewijs.
- Eventlabel, lokale datum/precisie, locatie en plaatsgevonden-basis.
- Gelokaliseerde titel/lead/body, oorspronkelijke Mood/Persona en claim-/bronreferenties.
- Eén hero-ID, maximaal twee extra assets; caption, alttekst, afmetingen, originele bron, maker, licentie/credit, content-/mediarevision en toegestaan bewerkingsbeleid.
- Persoonlijk actief, persoonlijke historie, gedeeld scherm en spraak afzonderlijk gekwalificeerd.
- Beheerde tijdelijke URLs en originele media-/bronrechten; geen permanente bearer in geschiedenis.
- Bestaande open/listen/ask-referenties; geen vrije uitvoerbare modelpayload.

Behoud bestaande v1/v2-werking en oudere consumers via minimale optionele/versioneerbare uitbreiding. Unknown types degraderen veilig, maar generieke tekstfallback telt niet als native foto-acceptatie. Niet alle clients tegelijk als algemene opleverblokkade introduceren.

## 7. Media, rechten en fetchveiligheid

Zoekvindbaarheid, lezen van een pagina, fotodisplay, modelverwerking, TTS, bewaren en gedeeld tonen zijn afzonderlijke doelen. Gebruik bestaande source policy. Makercredit alleen geeft geen toestemming. Bewaar concrete licentie-/voorwaardenbasis, maker, source-URL, toepasselijke doelgroepen, retention-/cropregels en relevante revisie.

Gebruik de bestaande media-eigenaar en beheerde fetch/proxy/decoder. Brede search is geen willekeurige URL-fetch op clientinvoer. HTTPS, private/loopback/link-local/metadatahosts uitsluiten, DNS/redirect/port per hop valideren, geen credentials/cookies doorsturen. MIME + magic/decode + dimensies + bytes/decompressielimieten controleren. Geen willekeurige HTML/SVG/scripts in de client uitvoeren.

Bronpagina's/captions zijn onbetrouwbare data, nooit instructies, toolmachtiging of nieuwe systeemregels. Source prompt injection mag geen effecten of privédata-exfiltratie veroorzaken. Unknown rights blijven candidate-only. Geen blanket fair-use- of vrij hergebruikbeleid.

Een vrije licentie moet niet onterecht dezelfde korte levensduur krijgen als een transporttoken. Autorisatie-expiry, provider-URL-expiry en gebruiksbasis zijn afzonderlijke zaken. Geef geen private imagegrant aan VibeCast omdat de foto al op iPhone staat.

## 8. Timing en levenscyclus

Onderzoek voorbereid uitvoeren binnen bestaande Session/Knowledge-workowners, zo nodig voor geverifieerde komende artiesten uit de echte queue. Prefetch is geen gegarandeerde volgende track en veroorzaakt geen Moment/audio. Configureer begrensde candidate/request/concurrency/token/byte/deadlinebudgetten; kleine batch (bijvoorbeeld drie events), hoogstens drie te publiceren beelden. Werkelijke productiegrenzen met echte bronnen meten, niet fictief beloven. Geen onbegrensd crawler of fetch per render/poll/reconnect.

Publieke brondata mag waar toegestaan beperkt hergebruikt worden; private tekst/context niet tussen profielen delen. Dedupe in-flight en op event/foto/invalshoek via bestaande toegestane Session-/historykennis; geen nieuwe luistervoorkeurendatabase. 429/5xx/backoff/provider-not-configured eerlijk zichtbaar in capability/diagnostiek zonder ruwe privéprompts.

Dit rijke type gebruikt het bestaande aanvullende verhalen-/Presencebudget. Het vervangt de korte aankondiging bij trackstart niet en verschijnt niet verplicht bij ieder nummer. Beeld/story moeten voor eerste publicatie gereed zijn; client mag daarna natuurlijk tijdelijk aan het downloaden zijn.

Vlak voor publicatie oorspronkelijke Session/Profile/artist/event, bronnen, beeld en actuele Mood/Persona-/contextrevisie controleren. Late research uit A mag B niet wijzigen. Als de oorspronkelijke artiest niet meer relevant is, geen oud verhaal als actuele aanleiding inhalen. Reeds gepubliceerde bijdragen blijven wel terug te lezen/te bespreken.

## 9. Blijvende sessiehistorie, geen vluchtige foto

Bewaar de geaccepteerde titel/lead/body, eventdata, oorspronkelijke muziekrelatie, geselecteerde foto-ID's/contentrevisies, captions/credits/rechten en noodzakelijke bron-/claimverwijzingen in de bestaande sessieopslag. Geen complete artikelen, onbegrensde searchpayloads, ruwe prompts, providerkeys of permanente signed URLs.

Heropenen genereert geen nieuw verhaal. Het gebruikt dezelfde foto van hetzelfde optreden. Een nieuwe resolutie van dezelfde foto kan; een ander concert niet. Stel voor dit type een eigen passende public-research/historybasis vast: een verlopen huidige-playbackgrant mag niet als enige grondslag het onafhankelijke concertverhaal permanent onbruikbaar maken.

Waar toegestaan, kan de bestaande media-eigenaar expliciet met begrensde persistente afgeleiden worden uitgebreid. Geen tweede mediastore of globale versoepeling van Spotify/no-store. Waar alleen tijdelijke beeldtoegang kan: bewaar de exacte bron/fotoidentiteit en herstel alleen die toegestane toegang. Maak die ontwerpkeuze en bronvoorwaarden expliciet.

Na latere 404/URL-expiry: bestaande tekst intact en rustige herstelstatus, geen afbeelding vervangen door een nieuwe artiestfoto. Hash/revisie controleren bij URL die andere bytes kan leveren. Een werkelijk ingetrokken gebruiksbasis krijgt passende withdrawal; tijdelijke onbereikbaarheid is niet automatisch rights revocation. Session/Profiledelete en bestaande retentionruiming verwijderen gebonden inhoud en afgeleiden. Geen eeuwige externe beeldbeschikbaarheid beloven.

## 10. Ask DJ, voice en playback

‘Vraag hierover’ gebruikt de bestaande gedeelde Ask DJ-service, gebonden aan oorspronkelijk Moment/event. ‘Wat gebeurde daar?’, ‘Wie speelde er mee?’ en ‘Vertel meer over dat podium’ blijven over die avond gaan na een trackwisseling. ‘Herhaal het’ spreekt hetzelfde verhaal; samenvatten/verdiepen zijn gewone nieuwe scoped antwoorden, geen herschrijven van geschiedenis.

HA-native voice #1532 kan deze content later consumeren. Het is geen voorwaarde voor de eerste Live-impressie. ‘Laat dat optreden zien’ vraagt een toegelaten gedeelde presentatie, geen nieuwe research-/download-/playbackroute.

De hero heeft geen automatische muziekplayactie. Studiotrack en concertopname niet verwisselen. Een bestaande geautoriseerde trackactie mag apart blijven met duidelijke betekenis; het openen van foto/verhaal wijzigt geen playback/queue en start geen microfoon. Geen video, concertstream of nieuwe autoplay in scope.

## 11. Laneverdeling en oplevervolgorde

**Core #1101:** primaire documentaire eigenaar en later producer: eventresearch, searchadapters, event-/foto-/claimbinding, narratie/review, Planner/publicatie, bestaande historie/media/speech, source security en gedeelde producer waar de canonieke rendererbron al in Core ligt.

**Apple #87:** bestaande Flow/history/media/TTS/Ask DJ consumer met media-first kaart/detail/viewer/credits; iPhone/iPad/Mac, vijf talen/a11y en echte visuele acceptatie. Geen opnieuw gebouwde app of tweede galerie-/gesprekkenservice.

**VibeCast #10:** shared foto/titel/lead/credit/focus vanuit geautoriseerde producer; bestaande pakket-/import/distributieroute. Geen vendorpatch, private grant, clientsearch of zelfstandige inhoud. Gedeeld screen/audio apart kwalificeren. Geen permanente chat op tv.

**Geen nieuwe API/APNs/ESP32/Pi/Website-opdracht.** Bestaande consumers krijgen alleen noodzakelijke compatibiliteit/regressies via hun owners. Nieuwe imageattachments op push/Watch/widgets vereisen aparte scope.

Volgorde: (A) docs + actuele hergebruikmatrix + minimale contract/fixtures; (B) research → exact event/photo → narratie → opgeslagen Moment; (C) persoonlijke Core/Apple verticale acceptatie; (D) gedeelde projectie/consumeracceptatie. Apple/VibeCast kunnen met echte voorgestelde fixtures ontwerp voorbereiden zonder te wachten op alle documentary finalizations. Geen hard dependency op volledige voiceadapter, room-routing, rich push, Voor jou of alle andere Momentfamilies.

## 12. Canonieke repositorydocumentatie

Integreer één productdocument en één technische companion, of bestaande gelijkwaardige documenten:
- `docs/product/LIVE_IMPRESSION_EXPERIENCE_V1.md`
- `docs/technical/LIVE_IMPRESSION_RESEARCH_MEDIA_CONTRACT_V1.md`

Neem daarin alle bovenstaande userflows, type/relatieverschillen, source/media/security/persistence, scopes en onderstaande testmatrix op. Werk gerichte verwijzingen bij vanuit bestaande artist research/photo, Moment/native/media/history/speech, Ask DJ en VibeCast-documenten. Registreer volgens de echte architectuurindex/ADR-conventie; verzin geen bestaande ADRnummers.

Werk de canonieke `docs/roadmap/v1/djconnect-platform-v1.json` en bestaande generatorprojecties voor CATALOGUE/DEPENDENCIES/OPEN_WORK/lanes bij. Hergebruik bestaande nodes waar de scope past; alleen ontbrekende Live-impressie producer-/consumer-/acceptatieleaves toevoegen. Echte functionele afhankelijkheden onderscheiden van writer-/host-/releasebeleid. Geen tweede backlog, geen handmatig concurrerende generated tabellen, geen oudere bronbewijzen als complete nieuwe functie herlabelen.

Apple/receiver documenteren hun lokale hergebruik-/UI-/testplan met verwijzing naar de centrale architectuur, niet nog een onafhankelijke volledige specificatie. Na beschermde documentdelivery verwijst dit intake-issue naar de exacte documenten/commit en open checklist; historie blijft behouden.

## 13. Acceptatie — concrete aantoonbare uitkomst

| ID | Scenario |
| --- | --- |
| LI-01 | Werkelijke web- én imagesearch → historisch optreden → opgehaalde hero → brononderbouwd verhaal. Handmatig gekozen fixture is niet het enige positieve bewijs. |
| LI-02 | Recent op concertdatum; nieuwe terugblik op oud event niet recent; toekomstig/afgelast event geen uitgevoerd concert. |
| LI-03 | Naamgenoot/tributeband/verkeerde datum/zaal/touravond worden niet samengevoegd. |
| LI-04 | Gemengde archieffoto's in één artikel: individuele juiste caption/asset/eventbinding vereist. |
| LI-05 | Ontbrekend beeld/rechten → geen nieuw leeg Live-impressie-Moment; normale sessie blijft werken. |
| LI-06 | Minimaal één, hoogstens drie echte scherpe beelden; geen cover/stock/AI/upscale-vervanging. |
| LI-07 | Artistcontext, lied daar gespeeld en exacte opnamebinding blijven verschillend in copy/acties. |
| LI-08 | iPhone/iPad/Mac echte hero/detail/credit, scroll/focusherstel en Dynamic Type/VoiceOver/keyboard. |
| LI-09 | Autoplay uit laat tekst/foto + handmatig Luister bestaan; TTS-fout verwijdert tekst niet; replay oorspronkelijke tekst. |
| LI-10 | Doorvragen blijft bij event na trackwissel; replay/heropenen maakt geen nieuw Moment of extra budgetcharge. |
| LI-11 | Herstart/historie toont oorspronkelijke tekst/event/foto, geen nieuwe generatie/Sessionstart. |
| LI-12 | Expired URL/404/andere bytes geeft herstel, geen ander concert; echte withdrawal onderscheiden. |
| LI-13 | Delete/retention/Profile- en bron-/doelgroepintrekking ruimen juiste inhoud/grants/afgeleiden op. |
| LI-14 | Prefetch/artistwisseling/einde/late callbacks/reconnect: geen verouderde of dubbele publicatie; Presence blijft eigenaar. |
| LI-15 | Broninjectie, SSRF/redirect, bad MIME/decode/oversize, 429/timeout en onbekende rechten veilig verwerkt. |
| LI-16 | VibeCast alleen shared toegestaan beeld/tekst/credits; geen private tokens/DNA of duplicate audio; clear bij einde. |
| LI-17 | Oudere client/unknown type degrades veilig; fallback niet als native feature-PASS verkopen. |
| LI-18 | Redactionele beoordeling van beeldkracht, echte avond/anekdote, stijl/variatie/feiten en vijf talen. |
| LI-19 | Meerdere artiesten/genres/sessies: event/foto/invalshoekvariatie zonder nieuw privévoorkeurenarchief. |
| LI-20 | Echte passende installatie: research → foto → narratie → publicatie → native zichtbaar → historie → replay/doorvraag. |

Minimaal historisch én recent brongeval, plus verkeerde-event/beeldrechten/onbeschikbaargevallen. Meet echte requestkosten/latency en native geheugen/beelddimensies; verzin geen prestatiegarantie. Onderscheid fixture/unit, echte publieke bronnen, live model, native screenshot/a11y, hoorbare TTS en fysieke gedeelde-tvacceptatie. De eerste complete persoonlijke feature hoeft niet op alle andere platforms te wachten.

## 14. Gelezen basis en primaire referenties

Core-main: `59d51e692c3c1681b6b9711edd1e2e52c363bf68`.
- `ARCHITECTURE_PRINCIPLES.md`, blob `470319398274a2c3c1ae74316997dc55d0ada09a`.
- `docs/product/PERSONAL_DJ_ARTIST_STORY_INTEGRATION_V1.md`, blob `6933e5b8fcc87c3425cddebfee13ea1570ca3d25`.
- `docs/product/SESSION_ARTIST_PHOTO_V2.md`, blob `83bb575681bf28cca91a467a16590422cafef65c`.
- `docs/product/SESSION_ARTWORK_DELIVERY_CONTRACT_V1.md`, blob `9a49471e13e6c0cd0ab7d4e3c93ae8fa3dc87f82`.
- Apple `SessionTimelineScreen.swift`, gedeeltelijk gelezen blob `7afc710a2666cab255f3e87d08feb12b00f50543`; exacte kaart/componentinventory door owning lane.

Primaire API-/bronreferenties gecontroleerd op 8 november 2026:
- https://api-dashboard.search.brave.com/api-reference/images/image_search
- https://api-dashboard.search.brave.com/app/documentation/image-search
- https://api.setlist.fm/docs/1.0/resource__1.0_search_setlists.html
- https://www.mediawiki.org/wiki/API:Imageinfo
- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- https://www.mediawiki.org/wiki/Wikimedia_APIs/Content_reuse
- https://api.openverse.org/v1/ — geïndexeerde referentie gevonden; directe read gaf 403 in deze sessie, geen operationele API-toegang bewezen.

Deze referenties bewijzen geen DJConnect-providerconfiguratie, betaalmandaat of toestemming voor elk gevonden beeld. Controleer werkelijk gekozen provider-/retentie-/commerciële voorwaarden tijdens implementation preflight.

**Opleverrapport:** opdracht vastgelegd; docs geschreven/PR/main; graph bijgewerkt; code geschreven; CI/review/merge; geïnstalleerde werking; visuele/redactionele en hoorbare acceptatie afzonderlijk. De documentaire stopgrens uit de intake is op 19 november 2026 vervangen door de expliciete integrale Core+Apple-implementatieopdracht; release en installatie blijven afzonderlijk.