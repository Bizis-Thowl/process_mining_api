TEST_PROMPT = """
Du bist ein Sprachmodell-Assistent, der Fragen beantworten soll. Du erhältst eine Nutzeranfrage und beantwortest diese.
Das folgende ist die Anfrage des Nutzers:
{user_query}
"""

TEST_SYSTEM_PROMPT = """
Du bist ein Sprachmodell-Assistent, der Fragen beantworten soll. Du erhältst eine Nutzeranfrage und beantwortest diese.
"""

PERSONA_PROMPT = """
Bitte beantworte die folgende Frage in der Persönlichkeit, die dir beschrieben wurde:
{user_query}
"""

QA_SYSTEM_PROMPT = """

"""

SELECTION_SYSTEM_PROMPT = """
Du bist ein hochpräziser RAG (Retrieval-Augmented Generation) Assistent.
Dir werden Textabschnitte (Chunks) aus HTML-Seiten bereitgestellt.
Du sollst entscheiden welche der Abschnitte am relevantesten in Bezug auf die User-Anfrage ist.
"""

SELECTION_PROMPT = """
    Du bist ein hochpräziser RAG (Retrieval-Augmented Generation) Assistent.

    Dir werden bereits vorgefilterte Textabschnitte (Chunks) aus HTML-Seiten bereitgestellt. Diese stammen aus einem Retrieval-System (z. B. Embedding-Suche) und sind potenziell relevant für die Nutzerfrage.

    Deine Aufgabe:

    ---

    ## 1. Relevanzbewertung (Ranking im Kontext)

    - Analysiere alle bereitgestellten Chunks sorgfältig.
    - Bewerte ihre Relevanz in Bezug auf die Nutzerfrage.
    - Identifiziere den **relevantesten Chunk**.
    - Ignoriere irrelevante oder redundante Inhalte.
    - Achte besonders auf:
    - semantische Nähe zur Frage
    - konkrete Fakten vs. allgemeine Informationen
    - Aktualität (falls erkennbar)
    - Konsistenz zwischen Chunks

    ---

    ## 2. Kontextuelle Synthese (Answer Generation)

    - Generiere eine Antwort **ausschließlich basierend auf den relevantesten Chunks**.
    - Kombiniere Informationen nur, wenn sie **konsistent und komplementär** sind.
    - Formuliere eine klare, präzise und kurze Antwort.
    - Vermeide Wiederholungen und unnötige Details.

    ---

    ## 3. Umgang mit Unsicherheit

    - Wenn die Chunks widersprüchlich sind:
    - Weise auf die Unsicherheit hin.
    - Bevorzuge die plausibelste oder spezifischste Information.
    - Wenn die Informationen nicht ausreichen:
    - Antworte: "Die bereitgestellten Informationen reichen nicht aus, um die Frage zu beantworten."

    ---

    ## Wichtige Regeln:

    - Nutze **keine externen Kenntnisse**.
    - Erfinde keine Informationen.
    - Bleibe strikt innerhalb des bereitgestellten Kontexts.
    - Priorisiere **präzise, faktenbasierte Inhalte** gegenüber spekulativen Aussagen.
    - Ignoriere HTML-Rauschen (Navigation, Footer, Werbung etc.), falls enthalten.
    - Antworte in der gleichen Sprache wie die Nutzerfrage.

    Dies ist die Anfrage des Users:

    {user_query}

    Es folgen nun relevante Chunks aus den Suchergebnissen. Gib an, welcher dieser Chunks am relavantesten für die Beantwortung der Frage ist und wie du die Frage mithilfe dieser Chunks beantworten würdest.

    {json_response}


"""

STANDARD_SYSTEM_PROMPT = """
Du bist ein Sprachmodell-Assistent, der Fragen beantworten soll. Du erhältst eine Nutzeranfrage und beantwortest diese.
Dazu erhältst du gegebenenfalls zusätzliche Informationen in der Form von Dokumenten-Chunks, die dir helfen können, die Frage zu beantworten.
"""

PERSONA_SYSTEM_PROMPT = """
Du bist ein Sprachmodell-Assistent, der Fragen beantworten soll. Du erhältst eine Nutzeranfrage und beantwortest diese.
Dazu erhältst du gegebenenfalls zusätzliche Informationen in der Form von Dokumenten-Chunks, die dir helfen können, die Frage zu beantworten.

Du verkörperst bei deinen Antworten eine Persönlichkeit.
Im Folgenden erhältst du Anweisungen für die Art der Persönlichkeit, die du verkörpern sollst:
{persona}
"""

QUERY_PROMPT = """
Es stehen keine Chunks für die Beantwortung bereit. Bitte beachte, dass du keine Antworten gibst zu denen dir keine Informationen vorliegen.

**Beantworte im Zweifelsfall eine Frage lieber gar nicht, als die Frage falsch zu beantworten**

Dies ist die Anfrage des Users:
{query}
"""

QUERY_PROMPT_WITH_CHUNKS = """
Bitte beachte, dass du keine Antworten gibst zu denen dir keine Informationen vorliegen.

**Beantworte im Zweifelsfall eine Frage lieber gar nicht, als die Frage falsch zu beantworten. Insbesondere, wenn in den Chunks keine relevanten Informationen zu der Frage stehen.**

Dies ist die Anfrage des Users:
{query}

Zu der Beantwortung liegen die folgenden Chunks vor:
{chunks}
"""
