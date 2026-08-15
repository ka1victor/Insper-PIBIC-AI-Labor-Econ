"""Passo 1 — Baixa os insumos de terceiros que a métrica de uso consome.

Único passo que precisa de rede, e opcional: o `dados/doses_por_ocupacao.csv`
que sai do passo 2 já vem no repositório. Rode os dois quando quiser refazer a
métrica do zero.

O que baixa, e de onde:

  três relatórios do Anthropic Economic Index, do conjunto Anthropic/EconomicIndex
  no HuggingFace: conversas classificadas por tarefa e por tipo de colaboração,
  nas janelas de agosto e novembro de 2025 e fevereiro de 2026;

  o universo de tarefas do O*NET, reconstruído de "Task Statements" mais
  "Occupation Data" do onetcenter.org, que é o denominador da métrica;

  as notas de importância da tarefa em cada ocupação ("Task Ratings"), que são
  os pesos da repartição fracionária.

Tudo vai para `dados/aei/`, que não é versionado: são cerca de 230 MB de dado de
terceiro, público e baixável por este comando.

**Cada arquivo é conferido depois de baixado.** Download truncado é o modo de
falha que custa caro aqui, porque não levanta erro: um "Task Ratings" pela metade
deixa a maioria dos pares sem nota de importância, a repartição cai no rateio
uniforme e a métrica sai ligeiramente diferente, sem que nada avise. Quem só
olhasse o código de saída do curl concluiria que deu certo.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comum

AUX = comum.DADOS / "aei"
AUX.mkdir(parents=True, exist_ok=True)

HF = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main"
AEI = [
    ("release_2025_09_15/data/output/aei_enriched_claude_ai_2025-08-04_to_2025-08-11.csv",
     "aei_enriched_claude_ai_2025-08-04_to_2025-08-11.csv", 20_000_000),
    ("release_2026_01_15/data/intermediate/aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv",
     "aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv", 80_000_000),
    ("release_2026_03_24/data/aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv",
     "aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv", 90_000_000),
]

# As versões do banco do O*NET mudam de caminho; tenta em ordem.
ONET_VERSOES = ["db_29_3_text", "db_29_1_text", "db_28_3_text"]
RATINGS_DEST = AUX / "onet_task_ratings.txt"
TAREFAS_DEST = AUX / "onet_task_statements.csv"

# Mínimos de sanidade. O Task Ratings completo tem cerca de 158 mil linhas; foi
# lido pela metade uma vez, e o efeito foi silencioso.
MIN_LINHAS_RATINGS = 100_000
MIN_LINHAS_TAREFAS = 15_000


def baixa(url, destino, tamanho_minimo):
    """Baixa com curl e confere o tamanho. Devolve True se o arquivo serve."""
    if destino.exists() and destino.stat().st_size >= tamanho_minimo:
        print(f"[1] {destino.name} já presente "
              f"({destino.stat().st_size / 1e6:.0f} MB) — pulando.")
        return True
    print(f"[1] baixando {destino.name}...")
    r = subprocess.run(["curl", "-fSL", "--retry", "3", "--retry-delay", "2",
                        "-o", str(destino), url], check=False)
    if r.returncode != 0:
        print(f"[1] FALHA de rede em {destino.name}.")
        return False
    tamanho = destino.stat().st_size if destino.exists() else 0
    if tamanho < tamanho_minimo:
        print(f"[1] FALHA: {destino.name} veio com {tamanho / 1e6:.1f} MB, "
              f"abaixo dos {tamanho_minimo / 1e6:.0f} MB esperados. "
              "Provável download truncado — apague o arquivo e rode de novo.")
        return False
    return True


def baixa_universo_onet():
    """Reconstrói o universo tarefa × ocupação da fonte primária do O*NET.

    São dois arquivos: "Task Statements" traz a tarefa por ocupação, e
    "Occupation Data" traz os títulos, de que a harmonização de código precisa
    para o casamento por título.
    """
    if TAREFAS_DEST.exists() and TAREFAS_DEST.stat().st_size > 1_000_000:
        print(f"[1] {TAREFAS_DEST.name} já presente — pulando.")
        return True
    for versao in ONET_VERSOES:
        base = f"https://www.onetcenter.org/dl_files/database/{versao}"
        tmp_t, tmp_o = AUX / "_tarefas.txt", AUX / "_ocupacoes.txt"
        ok = all(baixa(f"{base}/{arq}", dest, 50_000)
                 for arq, dest in [("Task%20Statements.txt", tmp_t),
                                   ("Occupation%20Data.txt", tmp_o)])
        if not ok:
            continue
        t = pd.read_csv(tmp_t, sep="\t", dtype=str)
        o = pd.read_csv(tmp_o, sep="\t", dtype=str)
        m = t.merge(o[["O*NET-SOC Code", "Title"]], on="O*NET-SOC Code", how="left")
        # "Task ID" viaja junto: é a chave que liga cada tarefa ao seu peso de
        # importância no Task Ratings.
        out = m[["O*NET-SOC Code", "Task ID", "Title", "Task"]].dropna(
            subset=["O*NET-SOC Code", "Task"])
        if len(out) < MIN_LINHAS_TAREFAS:
            print(f"[1] {versao} devolveu só {len(out):,} pares — tentando a próxima.")
            continue
        out.to_csv(TAREFAS_DEST, index=False)
        tmp_t.unlink(missing_ok=True)
        tmp_o.unlink(missing_ok=True)
        print(f"[1] universo O*NET reconstruído de {versao}: {len(out):,} pares "
              f"(tarefa × ocupação), {out['O*NET-SOC Code'].nunique()} ocupações.")
        return True
    print("[1] FALHA ao reconstruir o universo O*NET. Baixe 'Task Statements' e "
          "'Occupation Data' à mão em onetcenter.org (Database → text files).")
    return False


def confere_ratings():
    """O Task Ratings precisa estar inteiro, e o tamanho em bytes não basta."""
    if not RATINGS_DEST.exists():
        return False
    linhas = sum(1 for _ in RATINGS_DEST.open(encoding="utf-8", errors="ignore"))
    if linhas < MIN_LINHAS_RATINGS:
        print(f"[1] FALHA: onet_task_ratings.txt tem {linhas:,} linhas, abaixo "
              f"das {MIN_LINHAS_RATINGS:,} esperadas. Download truncado: apague "
              "o arquivo e rode de novo, ou a métrica sairá diferente sem avisar.")
        return False
    print(f"[1] onet_task_ratings.txt: {linhas:,} linhas, íntegro.")
    return True


def main():
    ok = True
    for caminho, nome, minimo in AEI:
        ok &= baixa(f"{HF}/{caminho}", AUX / nome, minimo)
    for versao in ONET_VERSOES:
        if baixa(f"https://www.onetcenter.org/dl_files/database/{versao}/"
                 "Task%20Ratings.txt", RATINGS_DEST, 8_000_000):
            break
    ok &= confere_ratings()
    ok &= baixa_universo_onet()
    if ok:
        print("[1] insumos prontos em dados/aei/. Próximo: 02_metricas.py")
    else:
        print("[1] algum insumo falhou — o passo 2 não roda sem eles.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
