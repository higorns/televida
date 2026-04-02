import json
import re
from datetime import datetime
from typing import Dict
from fastapi import FastAPI


class TriagemMedica:

    def __init__(self):
        self.sessao = {}
        self.etapa = "inicio"
        self.base_conhecimento = {
            "red_flags": {
                "dor_peito": "ALTO",
                "dificuldade_respirar": "ALTO",
                "confusao_mental": "ALTO",
                "sangramento": "ALTO",
                "febre_alta": "MODERADO"
            },
            "condutas": {
                "ALTO": "EMERGÊNCIA: Procure pronto-socorro IMEDIATAMENTE",
                "MODERADO": "Procure atendimento médico em 2-4 horas",
                "BAIXO": "Monitore sintomas, procure médico se piorarem"
            }
        }

    def iniciar(self):
        self.sessao = {
            "dados": {},
            "sintomas": [],
            "red_flags": [],
            "timestamp": datetime.now().isoformat()
        }
        self.etapa = "saudacao"
        return self.processar("")

    def processar(self, mensagem: str) -> str:
        if self.etapa == "saudacao":
            self.etapa = "nome"
            return "Olá! Sou seu assistente de triagem médica. Qual é o seu nome?"

        elif self.etapa == "nome":
            self.sessao["dados"]["nome"] = mensagem.strip()
            self.etapa = "idade"
            return f"Prazer, {mensagem.strip()}! Qual sua idade?"

        elif self.etapa == "idade":
            try:
                idade_match = re.search(r'\d+', mensagem)
                if not idade_match:
                    raise ValueError
                self.sessao["dados"]["idade"] = int(idade_match.group())
                self.etapa = "queixa"
                return "Qual o principal problema que está sentindo?"
            except:
                return "Por favor, informe apenas sua idade em números."

        elif self.etapa == "queixa":
            self.sessao["queixa_principal"] = mensagem
            self.etapa = "red_flags"
            return (
                "Responda SIM ou NÃO para cada item:\n"
                "1. Dor no peito?\n"
                "2. Dificuldade para respirar?\n"
                "3. Confusão mental/tontura intensa?\n"
                "4. Sangramento?\n"
                "5. Febre muito alta (>39°C)?"
            )

        elif self.etapa == "red_flags":
            self._verificar_red_flags(mensagem)
            self.etapa = "resultado"
            return self._gerar_resultado()

        return "Erro no processamento."

    def _verificar_red_flags(self, mensagem: str):
        texto = mensagem.lower()
        flags = []
        checks = [
            ("dor_peito", ["peito"]),
            ("dificuldade_respirar", ["respirar", "falta de ar"]),
            ("confusao_mental", ["confus", "tont"]),
            ("sangramento", ["sangr"]),
            ("febre_alta", ["febre", "39"])
        ]
        for flag, palavras in checks:
            if any(p in texto for p in palavras) and "sim" in texto:
                flags.append(flag)
        self.sessao["red_flags"] = flags

    def _gerar_resultado(self) -> str:
        red_flags = self.sessao["red_flags"]
        if any(self.base_conhecimento["red_flags"][f] == "ALTO" for f in red_flags):
            risco = "ALTO"
        elif any(self.base_conhecimento["red_flags"][f] == "MODERADO" for f in red_flags):
            risco = "MODERADO"
        else:
            risco = "BAIXO"

        resultado = {
            "classificacao": risco,
            "red_flags": red_flags,
            "conduta": self.base_conhecimento["condutas"][risco]
        }
        self._salvar_triagem(resultado)
        nome = self.sessao["dados"].get("nome", "Paciente")
        return (
            f"RESULTADO DA TRIAGEM - {nome}\n"
            f"CLASSIFICAÇÃO: {risco}\n"
            f"CONDUTA: {resultado['conduta']}\n"
            f"Esta triagem não substitui consulta médica."
        )

    def _salvar_triagem(self, resultado: Dict):
        log = {"timestamp": datetime.now().isoformat(), "sessao": self.sessao, "resultado": resultado}
        try:
            with open("triagem_logs.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Erro ao salvar log: {e}")


app = FastAPI()
triagem_instance = None


@app.get("/health")
def health():
    return {"status": "running"}


@app.post("/iniciar")
def iniciar_triagem():
    global triagem_instance
    triagem_instance = TriagemMedica()
    return {"status": "ok", "resposta": triagem_instance.iniciar()}


@app.post("/triagem")
def executar_triagem(payload: dict):
    global triagem_instance
    if triagem_instance is None:
        return {"status": "erro", "mensagem": "Sessão não iniciada. Chame /iniciar primeiro."}
    resposta = triagem_instance.processar(payload["mensagem"])
    return {
        "status": "ok",
        "etapa": triagem_instance.etapa,
        "resposta": resposta,
        "sessao": triagem_instance.sessao
    }
