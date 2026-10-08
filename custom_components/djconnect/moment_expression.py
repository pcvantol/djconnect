"""Authored local realization from immutable display anchors, never a model.

Persona lives in the factual sentence and its rhythm. No provider requests,
private context, fact extraction from prose or generic opener/footer chassis.
"""

from __future__ import annotations

from .session_facts import QualifiedSessionFact, SharedProducerFact, DisplayFactCore

PERSONAS = ("home_dj", "radio_dj", "club_dj", "festival_dj")
CONJUNCTIONS = {"en": "and", "nl": "en", "de": "und", "fr": "et", "es": "y"}
BE = {
    "en": ("is", "are"),
    "nl": ("is", "zijn"),
    "de": ("wird", "werden"),
    "fr": ("figure", "figurent"),
    "es": ("figura", "figuran"),
}
ROLE = {
    "en": ("a producer", "producers"),
    "nl": ("producer", "producers"),
    "de": ("Produzent", "Produzenten"),
    "fr": ("producteur", "producteurs"),
    "es": ("productor", "productores"),
}
CREDITS = {
    "nl": {
        "home_dj": (
            "Even meekijken in de credits: {n} {be} hier als {r} gecrediteerd.",
            "In de producercredits {stand} {n}. Die vermelding neem ik graag even mee.",
            "Bij de producerrol {stand} {n} vermeld.",
            "{n} {be} als {r} gecrediteerd bij deze opname; daar blijf ik heel even bij stilstaan.",
        ),
        "radio_dj": (
            "Bij deze opname horen ook de producercredits: {n}.",
            "{n} {be} als {r} gecrediteerd bij deze opname. Zo krijgt die credit ook een plek.",
            "Naast de titel {stand} {n} vermeld, in de producerrol.",
            "Een korte blik op de producercredits van deze opname brengt ons bij {n}.",
        ),
        "club_dj": (
            "{n}. Als {r} gecrediteerd bij deze opname.",
            "Als {r} gecrediteerd: {n}.",
            "De producercredits: {n}.",
            "{n} {be} hier als {r} vermeld.",
        ),
        "festival_dj": (
            "Ook even aandacht voor {n}: als {r} gecrediteerd bij deze opname.",
            "{n} {be} hier als {r} gecrediteerd. Die credit mag even in het licht.",
            "{n} {receive} hier een vermelding in de producercredits.",
            "De producercredits brengen {n} even naar voren. ",
        ),
    },
    "en": {
        "home_dj": (
            "Let's have a look together: {n} {be} credited here as {r}.",
            "The producer credits name {n}. I like to give that credit a moment, too.",
            "For the producer role, the credits list {n}.",
            "{n} {be} credited as {r} on this recording; a little detail worth pausing over.",
        ),
        "radio_dj": (
            "Alongside this recording, the producer credits name {n}.",
            "{n} {be} credited as {r} on this recording. That credit gets its place in the story, too.",
            "Beside the title, {n} {appear} in the producer credits.",
            "A brief look at the producer credits of this recording brings us to {n}.",
        ),
        "club_dj": (
            "{n}. Credited as {r} on this recording.",
            "Credited as {r}: {n}.",
            "The producer credits: {n}.",
            "{n} {be} listed here as {r}.",
        ),
        "festival_dj": (
            "A little attention for {n}, credited as {r} on this recording.",
            "{n} {be} credited here as {r}. That credit can have a little spotlight.",
            "{n} {get} a mention in the producer credits.",
            "The producer credits bring {n} forward for a moment. ",
        ),
    },
    "de": {
        "home_dj": (
            "Schauen wir gemeinsam in die Credits: {n} {be} hier als {r} genannt.",
            "In den Produktionscredits {de_stand} {n}. Diesen Credit nehme ich gern kurz mit.",
            "Für die Produzentenrolle nennen die Credits {n}.",
            "{n} {be} bei dieser Aufnahme als {r} genannt; bei diesem Detail bleibe ich kurz stehen.",
        ),
        "radio_dj": (
            "Zu dieser Aufnahme gehören auch die Produktionscredits: {n}.",
            "{n} {be} bei dieser Aufnahme als {r} genannt. So bekommt auch dieser Credit seinen Platz.",
            "Neben dem Titel {de_stand} {n} in den Produktionscredits.",
            "Ein kurzer Blick in die Produktionscredits dieser Aufnahme führt uns zu {n}.",
        ),
        "club_dj": (
            "{n}. Bei dieser Aufnahme als {r} genannt.",
            "Als {r} genannt: {n}.",
            "Die Produktionscredits: {n}.",
            "{n} {be} hier als {r} genannt.",
        ),
        "festival_dj": (
            "Auch kurz Aufmerksamkeit für {n}: bei dieser Aufnahme als {r} genannt.",
            "{n} {be} hier als {r} genannt. Dieser Credit darf kurz ins Licht.",
            "Die Produktionscredits nennen {n}.",
            "Die Produktionscredits rücken {n} kurz nach vorn. ",
        ),
    },
    "fr": {
        "home_dj": (
            "Regardons ensemble les crédits : {n} {be} ici comme {r}.",
            "Les crédits de production citent {n}. J'aime aussi accorder un instant à ce crédit.",
            "Les crédits de production citent {n}.",
            "{n} {be} comme {r} sur cet enregistrement ; un petit détail sur lequel s'arrêter.",
        ),
        "radio_dj": (
            "Aux côtés de cet enregistrement, les crédits de production citent {n}.",
            "{n} {be} comme {r} sur cet enregistrement. Ce crédit trouve aussi sa place dans le récit.",
            "À côté du titre, les crédits de production mentionnent {n}.",
            "Un bref regard sur les crédits de production de cet enregistrement nous mène à {n}.",
        ),
        "club_dj": (
            "{n}. Comme {r} dans les crédits de cet enregistrement.",
            "Dans les crédits comme {r} : {n}.",
            "Les crédits de production : {n}.",
            "{n} {be} ici comme {r}.",
        ),
        "festival_dj": (
            "Un peu d’attention aussi pour {n}, dans les crédits comme {r} sur cet enregistrement.",
            "{n} {be} ici comme {r}. Ce crédit peut avoir son petit coup de projecteur.",
            "Les crédits de production donnent ici leur place à {n}. ",
            "Les crédits de production mettent un instant {n} en avant. ",
        ),
    },
    "es": {
        "home_dj": (
            "Miremos juntos los créditos: {n} {be} aquí como {r}.",
            "En los créditos de producción {es_appear} {n}. También me gusta dedicar un momento a ese crédito.",
            "Los créditos de producción mencionan a {n}.",
            "{n} {be} como {r} en esta grabación; un pequeño detalle en el que detenernos.",
        ),
        "radio_dj": (
            "Junto a esta grabación, los créditos de producción mencionan a {n}.",
            "{n} {be} como {r} en esta grabación. Ese crédito también encuentra su lugar en el relato.",
            "Junto al título, los créditos de producción incluyen a {n}.",
            "Una breve mirada a los créditos de producción de esta grabación nos lleva a {n}.",
        ),
        "club_dj": (
            "{n}. En los créditos como {r} de esta grabación.",
            "En los créditos como {r}: {n}.",
            "Los créditos de producción: {n}.",
            "{n} {be} aquí como {r}.",
        ),
        "festival_dj": (
            "Un momento de atención también para {n}, en los créditos como {r} de esta grabación.",
            "{n} {be} aquí como {r}. Ese crédito puede tener su momento de atención.",
            "Los créditos de producción dan aquí su lugar a {n}. ",
            "Los créditos de producción ponen un instante a {n} en primer plano. ",
        ),
    },
}
CALLBACKS = {
    "nl": {
        "home_dj": (
            "{p} kwamen we eerder tegen bij «{b}», als producer. Bij «{c}» staat die naam opnieuw in de producercredits.",
            "{p} noemden we eerder bij «{b}», als producer. Ook «{c}» geeft {p} die credit.",
            "In de producercredits van «{c}» staat {p}. Een bekende naam uit onze eerdere bijdrage over «{b}», in diezelfde rol.",
            "In de credits van «{c}» staat {p} als producer. Die naam noemden we eerder al bij «{b}», in dezelfde rol.",
        ),
        "radio_dj": (
            "De producercredits van «{c}» brengen ons terug bij de eerder besproken opname «{b}»: {p} staat bij beide in die rol vermeld.",
            "Van de eerder besproken «{b}» naar «{c}» loopt een lijn door de producercredits: {p} staat bij beide als producer vermeld.",
            "{p} staat bij «{c}» als producer gecrediteerd. Diezelfde naam en rol kennen we uit de eerdere bijdrage over «{b}».",
            "Voor de producercredits brengt «{c}» ons terug bij «{b}», dat we eerder bespraken: op beide opnamen staat {p} als producer vermeld.",
        ),
        "club_dj": (
            "{p}: producer op «{c}». Ook bij «{b}», dat we eerder bespraken.",
            "«{c}»: {p} als producer. Dezelfde credit als bij de eerder besproken «{b}».",
            "De producercredit gaat ook hier naar {p}. Net als bij «{b}», dat we eerder bespraken; nu bij «{c}».",
            "{p} staat als producer bij «{c}» — en bij «{b}», dat we eerder bespraken.",
        ),
        "festival_dj": (
            "Daar is {p} weer in de producercredits: bij «{c}», en eerder bij de besproken opname «{b}».",
            "«{c}» noemt {p} in de producercredits. Een naam die we eerder bij «{b}» bespraken, in dezelfde rol.",
            "«{c}» en de eerder besproken «{b}» delen de producercredit voor {p}. ",
            "«{c}» en de eerder besproken «{b}» ontmoeten elkaar in de credits: {p} staat op beide vermeld als producer.",
        ),
    },
    "en": {
        "home_dj": (
            "We met the name {p} earlier in the producer credits for “{b}”. “{c}” credits that name in the same role.",
            "We mentioned {p} earlier as a producer on “{b}”. “{c}” gives {p} that credit, too.",
            "The producer credits for “{c}” name {p}. A familiar name from our earlier contribution about “{b}”, in that same role.",
            "“{c}” lists {p} as a producer. We mentioned that name earlier on “{b}”, in the same role.",
        ),
        "radio_dj": (
            "The producer credits for “{c}” take us back to the earlier-discussed recording “{b}”: {p} is named in that role on both.",
            "From the earlier-discussed “{b}” to “{c}”, a line runs through the producer credits: {p} is credited on both recordings.",
            "“{c}” credits {p} as a producer. We know that same name and role from our earlier contribution about “{b}”.",
            "For the producer credits, “{c}” takes us back to “{b}”, which we discussed earlier: both recordings credit {p} as a producer.",
        ),
        "club_dj": (
            "{p}: producer on “{c}”. Also on “{b}”, which we discussed earlier.",
            "“{c}”: {p} as a producer. The same credit as on the earlier-discussed “{b}”.",
            "A producer credit for {p} here, too. Like on “{b}”, which we discussed earlier; this time on “{c}”.",
            "{p} is credited as a producer on “{c}” — and on “{b}”, which we discussed earlier.",
        ),
        "festival_dj": (
            "There is {p} again in the producer credits: on “{c}”, and earlier in our discussion of “{b}”.",
            "“{c}” names {p} in the producer credits. A name we discussed earlier on “{b}”, in the same role.",
            "“{c}” and the earlier-discussed “{b}” share a producer credit for {p}. ",
            "“{c}” and the earlier-discussed “{b}” meet in the credits: both name {p} as a producer.",
        ),
    },
    "de": {
        "home_dj": (
            "Den Namen {p} sahen wir zuvor in den Produktionscredits von „{b}“. „{c}“ nennt diesen Namen in derselben Rolle.",
            "Bei „{b}“ nannten wir {p} zuvor als Produzenten. Auch „{c}“ nennt {p} in dieser Rolle.",
            "In den Produktionscredits von „{c}“ steht {p}. Ein bekannter Name aus unserem früheren Beitrag über „{b}“, in derselben Rolle.",
            "„{c}“ nennt {p} als Produzenten. Diesen Namen erwähnten wir zuvor bei „{b}“ in derselben Rolle.",
        ),
        "radio_dj": (
            "Die Produktionscredits von „{c}“ führen zur zuvor besprochenen Aufnahme „{b}“ zurück: {p} wird bei beiden in dieser Rolle genannt.",
            "Von der zuvor besprochenen Aufnahme „{b}“ zu „{c}“ verläuft eine Linie durch die Produktionscredits: {p} wird bei beiden als Produzent genannt.",
            "Bei „{c}“ wird {p} als Produzent genannt. Denselben Namen und dieselbe Rolle kennen wir aus dem früheren Beitrag über „{b}“.",
            "Für die Produktionscredits führt uns „{c}“ zu „{b}“ zurück, das wir zuvor besprochen haben: Beide Aufnahmen nennen {p} als Produzenten.",
        ),
        "club_dj": (
            "{p}: Produzent bei „{c}“. Auch bei „{b}“, das wir zuvor besprochen haben.",
            "„{c}“: {p} als Produzent. Derselbe Credit wie bei der zuvor besprochenen Aufnahme „{b}“.",
            "Auch hier ein Produzentencredit für {p}. Wie bei „{b}“, das wir zuvor besprochen haben; jetzt bei „{c}“.",
            "{p} wird bei „{c}“ als Produzent genannt — und bei „{b}“, das wir zuvor besprochen haben.",
        ),
        "festival_dj": (
            "Da ist {p} wieder in den Produktionscredits: bei „{c}“ und zuvor in unserem Beitrag über „{b}“.",
            "„{c}“ nennt {p} in den Produktionscredits. Ein Name aus unserem früheren Beitrag über „{b}“, in derselben Rolle.",
            "„{c}“ und die zuvor besprochene Aufnahme „{b}“ teilen einen Produzentencredit für {p}. ",
            "„{c}“ und die zuvor besprochene Aufnahme „{b}“ begegnen sich in den Credits: Beide nennen {p} als Produzenten.",
        ),
    },
    "fr": {
        "home_dj": (
            "Nous avions vu le nom de {p} dans les crédits de production sur « {b} ». « {c} » cite ce nom dans le même rôle.",
            "Nous avions cité {p} à la production sur « {b} ». « {c} » donne aussi ce crédit à {p}.",
            "Les crédits de production sur « {c} » citent {p}. Un nom familier de notre intervention précédente sur « {b} », dans le même rôle.",
            "« {c} » cite {p} à la production. Nous avions déjà mentionné ce nom dans le même rôle sur « {b} ».",
        ),
        "radio_dj": (
            "Les crédits de production sur « {c} » nous ramènent à l’enregistrement évoqué précédemment, « {b} » : {p} figure dans ce rôle sur les deux.",
            "De l’enregistrement évoqué précédemment, « {b} », à « {c} », un fil passe par les crédits de production : {p} figure sur les deux.",
            "Sur « {c} », {p} figure à la production. Nous connaissons ce même nom et ce même rôle de notre intervention précédente sur « {b} ».",
            "Pour les crédits de production, « {c} » nous ramène à « {b} », que nous avions évoqué : {p} figure à la production sur les deux enregistrements.",
        ),
        "club_dj": (
            "{p} : à la production sur « {c} ». Aussi sur « {b} », que nous avions évoqué.",
            "« {c} » : {p} à la production. Le même crédit que sur « {b} », évoqué précédemment.",
            "Ici aussi, un crédit de production pour {p}. Comme sur « {b} », que nous avions évoqué ; cette fois sur « {c} ».",
            "{p} figure à la production sur « {c} » — et sur « {b} », que nous avions évoqué.",
        ),
        "festival_dj": (
            "Voici de nouveau {p} dans les crédits de production : sur « {c} », et auparavant dans notre échange sur « {b} ».",
            "« {c} » cite {p} à la production. Un nom évoqué auparavant sur « {b} », dans le même rôle.",
            "« {c} » et l’enregistrement évoqué précédemment, « {b} », partagent un crédit de production pour {p}. ",
            "« {c} » et l’enregistrement évoqué précédemment, « {b} », se rencontrent dans les crédits : {p} figure à la production sur les deux.",
        ),
    },
    "es": {
        "home_dj": (
            "Ya vimos el nombre de {p} en los créditos de producción de «{b}». «{c}» incluye ese nombre en el mismo papel.",
            "En «{b}» mencionamos antes a {p} como productor. «{c}» también da ese crédito a {p}.",
            "Los créditos de producción de «{c}» incluyen a {p}. Un nombre conocido de nuestra intervención anterior sobre «{b}», en ese mismo papel.",
            "«{c}» incluye a {p} como productor. Ya habíamos mencionado ese nombre en el mismo papel en «{b}».",
        ),
        "radio_dj": (
            "Los créditos de producción de «{c}» nos llevan a la grabación comentada antes, «{b}»: {p} figura en ese papel en ambas.",
            "De la grabación comentada antes, «{b}», a «{c}», un hilo pasa por los créditos de producción: {p} figura en ambas.",
            "En «{c}», {p} figura como productor. Conocemos ese mismo nombre y papel de nuestra intervención anterior sobre «{b}».",
            "Para los créditos de producción, «{c}» nos lleva de nuevo a «{b}», que comentamos antes: ambas grabaciones incluyen a {p} como productor.",
        ),
        "club_dj": (
            "{p}: productor en «{c}». También en «{b}», que comentamos antes.",
            "«{c}»: {p} como productor. El mismo crédito que en «{b}», comentada antes.",
            "Aquí también, un crédito de productor para {p}. Como en «{b}», que comentamos antes; esta vez en «{c}».",
            "{p} figura como productor en «{c}» — y en «{b}», que comentamos antes.",
        ),
        "festival_dj": (
            "Ahí vuelve {p} a los créditos de producción: en «{c}», y antes en nuestra intervención sobre «{b}».",
            "«{c}» incluye a {p} en los créditos de producción. Un nombre que comentamos antes en «{b}», en el mismo papel.",
            "«{c}» y la grabación comentada antes, «{b}», comparten un crédito de productor para {p}. ",
            "«{c}» y la grabación comentada antes, «{b}», se encuentran en los créditos: ambas incluyen a {p} como productor.",
        ),
    },
}
DOMAINS = {
    "en": ("instruments", "vocals", "composition"),
    "nl": ("de instrumenten", "de zang", "de compositie"),
    "de": ("die Instrumente", "den Gesang", "die Komposition"),
    "fr": ("les instruments", "les voix", "la composition"),
    "es": ("los instrumentos", "las voces", "la composición"),
}
OTHER_ROLES = {
    "en": (
        "{n} {be} credited for {d}.",
        "For {d}, the credits name {n}.",
        "{d_cap}: {n}, credited on this recording.",
        "This recording lists {n} for {d}.",
    ),
    "nl": (
        "{n} {be} gecrediteerd voor {d}.",
        "Voor {d} vermelden de credits {n}.",
        "{d_cap}: {n}, gecrediteerd bij deze opname.",
        "Deze opname noemt {n} voor {d}.",
    ),
    "de": (
        "{n} {be} für {d} in den Credits genannt.",
        "Für {d} nennen die Credits {n}.",
        "{d_cap}: {n}, in den Credits dieser Aufnahme.",
        "Diese Aufnahme nennt {n} für {d}.",
    ),
    "fr": (
        "{n} {be} dans les crédits pour {d}.",
        "Pour {d}, les crédits citent {n}.",
        "{d_cap} : {n}, dans les crédits de cet enregistrement.",
        "Cet enregistrement cite {n} pour {d}.",
    ),
    "es": (
        "{n} {be} en los créditos de {d}.",
        "Para {d}, los créditos mencionan a {n}.",
        "{d_cap}: {n}, en los créditos de esta grabación.",
        "Esta grabación incluye a {n} en {d}.",
    ),
}
EDITION = {
    "en": (
        "A little date beside this edition of {s}: Spotify lists {d}.",
        "For this edition of {s}, Spotify gives {d} as its date.",
        "This edition of {s}: {d}, according to Spotify.",
        "This edition of {s} gets its date too: {d}, as listed by Spotify.",
    ),
    "nl": (
        "Een datum bij deze uitgave van {s}: Spotify vermeldt {d}.",
        "Voor deze uitgave van {s} noemt Spotify {d} als datum.",
        "Deze uitgave van {s}: {d}, volgens Spotify.",
        "Ook deze uitgave van {s} krijgt haar datum erbij: {d}, zoals Spotify die vermeldt.",
    ),
    "de": (
        "Ein Datum zu dieser Ausgabe von {s}: Spotify nennt {d}.",
        "Für diese Ausgabe von {s} nennt Spotify das Datum {d}.",
        "Diese Ausgabe von {s}: {d}, laut Spotify.",
        "Auch diese Ausgabe von {s} bekommt ihr Datum dazu: {d}, wie Spotify es angibt.",
    ),
    "fr": (
        "Une date pour cette édition de {s} : Spotify indique {d}.",
        "Pour cette édition de {s}, Spotify indique la date {d}.",
        "Cette édition de {s} : {d}, selon Spotify.",
        "Cette édition de {s} a aussi sa date : {d}, telle que Spotify l’indique.",
    ),
    "es": (
        "Una fecha para esta edición de {s}: Spotify indica {d}.",
        "Para esta edición de {s}, Spotify señala la fecha {d}.",
        "Esta edición de {s}: {d}, según Spotify.",
        "Esta edición de {s} también tiene su fecha: {d}, tal como la indica Spotify.",
    ),
}
BIRTH = {
    "en": (
        "A small detail about {s}: the recorded birth date is {d}.",
        "A brief biographical note on {s}: the birth date is recorded as {d}.",
        "Birth date of {s}: {d}.",
        "A date beside the name {s}: {d}, the recorded birth date.",
    ),
    "nl": (
        "Een klein detail bij {s}: de vastgelegde geboortedatum is {d}.",
        "Een korte biografische voetnoot bij {s}: als geboortedatum staat {d} vermeld.",
        "Geboortedatum van {s}: {d}.",
        "Ook bij de naam {s} hoort een datum: {d}, de vermelde geboortedatum.",
    ),
    "de": (
        "Ein kleines Detail zu {s}: Als Geburtsdatum ist {d} angegeben.",
        "Eine kurze biografische Notiz zu {s}: Das angegebene Geburtsdatum ist {d}.",
        "Geburtsdatum von {s}: {d}.",
        "Auch zum Namen {s} gehört ein Datum: {d}, das angegebene Geburtsdatum.",
    ),
    "fr": (
        "Un petit détail sur {s} : la date de naissance indiquée est {d}.",
        "Une brève note biographique sur {s} : la date de naissance indiquée est {d}.",
        "Date de naissance de {s} : {d}.",
        "Une date à côté du nom de {s} : {d}, la date de naissance indiquée.",
    ),
    "es": (
        "Un pequeño detalle sobre {s}: la fecha de nacimiento indicada es {d}.",
        "Una breve nota biográfica sobre {s}: la fecha de nacimiento indicada es {d}.",
        "Fecha de nacimiento de {s}: {d}.",
        "Una fecha junto al nombre de {s}: {d}, la fecha de nacimiento indicada.",
    ),
}
FORMATION = {
    "en": (
        "A small detail about {s}: the formation date is recorded as {d}.",
        "For the beginning of {s}, the recorded formation date is {d}.",
        "Formation date of {s}: {d}.",
        "A date beside the name {s}: {d}, the recorded formation date.",
    ),
    "nl": (
        "Een klein detail bij {s}: voor de oprichting staat {d} vermeld.",
        "Voor het begin van {s} staat {d} als oprichtingsdatum vermeld.",
        "Oprichtingsdatum van {s}: {d}.",
        "Ook bij de naam {s} hoort een datum: {d}, de vermelde oprichtingsdatum.",
    ),
    "de": (
        "Ein kleines Detail zu {s}: Als Gründungsdatum ist {d} angegeben.",
        "Für den Beginn von {s} ist {d} als Gründungsdatum angegeben.",
        "Gründungsdatum von {s}: {d}.",
        "Auch zum Namen {s} gehört ein Datum: {d}, das angegebene Gründungsdatum.",
    ),
    "fr": (
        "Un petit détail sur {s} : la date de formation indiquée est {d}.",
        "Pour les débuts de {s}, la date de formation indiquée est {d}.",
        "Date de formation de {s} : {d}.",
        "Une date à côté du nom de {s} : {d}, la date de formation indiquée.",
    ),
    "es": (
        "Un pequeño detalle sobre {s}: la fecha de formación indicada es {d}.",
        "Para el comienzo de {s}, la fecha de formación indicada es {d}.",
        "Fecha de formación de {s}: {d}.",
        "Una fecha junto al nombre de {s}: {d}, la fecha de formación indicada.",
    ),
}
COMPOSERS = {
    "en": (
        "For the underlying composition, the credits name {n}. ",
        "The composition behind this recording credits {n}.",
        "Composition credits for the underlying work: {n}.",
        "The underlying work brings {n} into the composition credits.",
    ),
    "nl": (
        "Voor de onderliggende compositie noemen de credits {n}. ",
        "Het werk achter deze opname vermeldt {n} in de componistenrol.",
        "Compositiecredits van het onderliggende werk: {n}.",
        "Het onderliggende werk brengt {n} in de compositiecredits naar voren.",
    ),
    "de": (
        "Für die zugrunde liegende Komposition nennen die Credits {n}. ",
        "Das Werk hinter dieser Aufnahme nennt {n} für die Komposition.",
        "Kompositionscredits des zugrunde liegenden Werks: {n}.",
        "Das zugrunde liegende Werk rückt {n} in den Kompositionscredits nach vorn.",
    ),
    "fr": (
        "Pour la composition sous-jacente, les crédits citent {n}. ",
        "L’œuvre derrière cet enregistrement cite {n} à la composition.",
        "Crédits de composition de l’œuvre sous-jacente : {n}.",
        "L’œuvre sous-jacente met {n} en avant dans les crédits de composition.",
    ),
    "es": (
        "Para la composición subyacente, los créditos mencionan a {n}. ",
        "La obra detrás de esta grabación incluye a {n} en la composición.",
        "Créditos de composición de la obra subyacente: {n}.",
        "La obra subyacente pone a {n} en primer plano en los créditos de composición.",
    ),
}
HEADINGS = {
    "en": (
        "A look at the credits",
        "Names beside the recording",
        "Credits",
        "Names in the spotlight",
    ),
    "nl": ("Even de credits erbij", "Namen bij de opname", "Credits", "Namen in het licht"),
    "de": ("Ein Blick in die Credits", "Namen zur Aufnahme", "Credits", "Namen im Licht"),
    "fr": (
        "Un regard sur les crédits",
        "Des noms sur l’enregistrement",
        "Crédits",
        "Des noms en lumière",
    ),
    "es": (
        "Una mirada a los créditos",
        "Nombres de la grabación",
        "Créditos",
        "Nombres en primer plano",
    ),
}
DESCRIPTION = {
    "en": (
        "The short description of {s} reads: “{d}”.",
        "In the short description, {s} is introduced as “{d}”.",
        "{s}: “{d}”, from the short description.",
        "The short description gives {s} this introduction: “{d}”.",
    ),
    "nl": (
        "De korte beschrijving van {s} luidt: “{d}”.",
        "In de korte beschrijving wordt {s} voorgesteld als “{d}”.",
        "{s}: “{d}”, uit de korte beschrijving.",
        "De korte beschrijving stelt {s} zo voor: “{d}”.",
    ),
    "de": (
        "Die Kurzbeschreibung von {s} lautet: „{d}“.",
        "In der Kurzbeschreibung wird {s} als „{d}“ vorgestellt.",
        "{s}: „{d}“, aus der Kurzbeschreibung.",
        "Die Kurzbeschreibung stellt {s} so vor: „{d}“.",
    ),
    "fr": (
        "La courte description de {s} dit : « {d} ».",
        "Dans la courte description, {s} est présenté ainsi : « {d} ».",
        "{s} : « {d} », d’après la courte description.",
        "La courte description présente {s} ainsi : « {d} ».",
    ),
    "es": (
        "La descripción breve de {s} dice: «{d}».",
        "En la descripción breve, {s} se presenta como «{d}».",
        "{s}: «{d}», de la descripción breve.",
        "La descripción breve presenta así a {s}: «{d}».",
    ),
}


def joined(names: tuple[str, ...], locale: str) -> str:
    return (
        names[0]
        if len(names) == 1
        else ", ".join(names[:-1]) + f" {CONJUNCTIONS[locale]} " + names[-1]
    )


def realize(
    fact: QualifiedSessionFact, *, locale: str, persona: str, form: int, mood: str
) -> tuple[str, str] | None:
    lang = locale[:2].lower()
    if lang not in CREDITS or persona not in PERSONAS or fact.copy_for(locale) is None:
        return None
    profile = PERSONAS.index(persona)
    syntax = form % 4
    callback = isinstance(fact, SharedProducerFact)
    if callback:
        current, previous = fact.recording_evidence, fact.previous_evidence
        if current is None or previous is None:
            return None
        p = next(
            (credit for credit in current.producers if credit.contributor_id == fact.producer_id),
            None,
        )
        if p is None:
            return None
        body = CALLBACKS[lang][persona][syntax].format(p=p.name, c=current.title, b=previous.title)
    else:
        core = fact.display_core
        if type(core) is DisplayFactCore and core.validates(fact):
            if core.kind == "recording_credits":
                lines = []
                for role, names in core.roles:
                    n = joined(names, lang)
                    if role == "producer":
                        template = CREDITS[lang][persona][syntax]
                        singular = len(names) == 1
                        line = template.format(
                            n=n,
                            r=ROLE[lang][not singular],
                            be=BE[lang][not singular],
                            stand="staat" if singular else "staan",
                            appear="appears" if singular else "appear",
                            get="gets" if singular else "get",
                            receive="krijgt" if singular else "krijgen",
                            de_stand="steht" if singular else "stehen",
                            es_appear="aparece" if singular else "aparecen",
                        )
                    else:
                        d = DOMAINS[lang][("instrument", "vocal", "composer").index(role)]
                        line = OTHER_ROLES[lang][(profile + syntax) % 4].format(
                            n=n, d=d, d_cap=d[0].upper() + d[1:], be=BE[lang][len(names) > 1]
                        )
                    lines.append(line)
                body = " ".join(lines)
            elif core.kind == "work_composers":
                body = COMPOSERS[lang][profile].format(n=joined(core.roles[0][1], lang))
            else:
                templates = (
                    EDITION[lang]
                    if core.kind == "album_release"
                    else (BIRTH[lang] if core.entity_type == "Person" else FORMATION[lang])
                )
                body = templates[profile].format(s=core.subject, d=core.date)
        elif fact.key == "artist_description":
            body = DESCRIPTION[lang][profile].format(
                s=fact.copy_for(locale)[0], d=fact.copy_for(locale)[1]
            )
        else:
            return None
    summary = (
        fact.copy_for(locale)[0]
        if fact.key not in {"recording_credits", "shared_producer"}
        else HEADINGS[lang][profile]
    )
    return summary, body.strip()
