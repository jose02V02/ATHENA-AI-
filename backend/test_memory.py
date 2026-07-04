from app.core.memory_manager import memory

# 1. Test di inserimento
# Aggiungiamo un'informazione nella memoria di Athena
test_text = "Athena v0.2 utilizza Qdrant per la memoria a lungo termine."
memory.add_memory(test_text, {"topic": "architettura", "version": "0.2"})
print("✅ Memoria inserita correttamente!")

# 2. Test di ricerca (recupero)
# Chiediamo ad Athena di cercare qualcosa di simile
risultati = memory.search_memory("Come funziona la memoria di Athena?")

print("✅ Risultati trovati dal database:")
for r in risultati:
    print(f"- {r.get('text')}")