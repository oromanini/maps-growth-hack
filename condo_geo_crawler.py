#!/usr/bin/env python3
"""Crawler de condomínios horizontais de alto padrão usando Google Places API.

Saída em CSV com nome, cidade, endereço completo, latitude e longitude.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterable

import googlemaps


# =========================
# Configurações editáveis
# =========================
CIDADES_PADRAO = ["Maringá", "Londrina", "Sarandi"]
TERMOS_BUSCA_PADRAO = [
    "Condomínio Fechado",
    "Condomínio Residencial",
    "Resort Residence",
    "Loteamento Fechado",
]

# Heurística para focar em condomínios horizontais e evitar empreendimentos populares/comerciais.
PALAVRAS_POSITIVAS = {
    "condominio",
    "condomínio",
    "residencial",
    "residence",
    "village",
    "jardim",
    "park",
    "parque",
    "loteamento",
    "horizontal",
    "fechado",
}

PALAVRAS_NEGATIVAS = {
    "minha casa minha vida",
    "mcmv",
    "apartamento",
    "apartamentos",
    "edificio",
    "edifício",
    "comercial",
    "corporate",
    "business",
    "office",
    "loja",
    "galeria",
    "shopping",
    "hotel",
    "pousada",
    "república",
    "kitnet",
}

# Tipos comuns em locais comerciais para reduzir falso positivo.
TIPOS_NEGATIVOS = {
    "shopping_mall",
    "lodging",
    "store",
    "real_estate_agency",
    "point_of_interest",  # não exclui sozinho, mas reduz score quando combinado.
}


def normalizar_texto(valor: str) -> str:
    return " ".join((valor or "").lower().strip().split())


@dataclass
class CondoResult:
    nome: str
    cidade: str
    endereco: str
    latitude: float | None
    longitude: float | None


class CondoCrawler:
    def __init__(self, api_key: str, pause_seconds: float = 2.0) -> None:
        self.client = googlemaps.Client(key=api_key)
        self.pause_seconds = pause_seconds

    def buscar(self, cidades: Iterable[str], termos: Iterable[str]) -> list[CondoResult]:
        resultados: list[CondoResult] = []
        vistos_place_id: set[str] = set()

        for cidade in cidades:
            for termo in termos:
                query = f"{termo} em {cidade}, Paraná, Brasil"
                logging.info("Buscando: %s", query)

                try:
                    page = self.client.places(query=query, language="pt-BR")
                except Exception as exc:
                    logging.exception("Falha em places() para '%s': %s", query, exc)
                    continue

                while True:
                    for item in page.get("results", []):
                        place_id = item.get("place_id")
                        if not place_id or place_id in vistos_place_id:
                            continue

                        vistos_place_id.add(place_id)
                        detalhe = self._buscar_detalhes(place_id)
                        if not detalhe:
                            continue

                        nome = detalhe.get("name", "")
                        endereco = detalhe.get("formatted_address", "")
                        tipos = detalhe.get("types", [])
                        geometry = detalhe.get("geometry", {}).get("location", {})
                        lat = geometry.get("lat")
                        lng = geometry.get("lng")

                        if not self._aprovado_por_qualidade(nome, endereco, tipos):
                            continue

                        resultados.append(
                            CondoResult(
                                nome=nome,
                                cidade=cidade,
                                endereco=endereco,
                                latitude=lat,
                                longitude=lng,
                            )
                        )

                    token = page.get("next_page_token")
                    if not token:
                        break

                    time.sleep(self.pause_seconds)
                    try:
                        page = self.client.places(query=query, page_token=token, language="pt-BR")
                    except Exception as exc:
                        logging.exception("Falha ao buscar próxima página para '%s': %s", query, exc)
                        break

        return resultados

    def _buscar_detalhes(self, place_id: str) -> dict | None:
        try:
            data = self.client.place(
                place_id=place_id,
                language="pt-BR",
                fields=["name", "formatted_address", "geometry", "types"],
            )
            return data.get("result", {})
        except Exception as exc:
            logging.warning("Erro ao obter detalhes (%s): %s", place_id, exc)
            return None

    def _aprovado_por_qualidade(self, nome: str, endereco: str, tipos: list[str]) -> bool:
        texto = f"{normalizar_texto(nome)} {normalizar_texto(endereco)}"
        score = 0

        positivos = sum(1 for palavra in PALAVRAS_POSITIVAS if palavra in texto)
        negativos = sum(1 for palavra in PALAVRAS_NEGATIVAS if palavra in texto)

        score += positivos * 2
        score -= negativos * 3

        tipos_set = set(tipos or [])
        if "premise" in tipos_set or "subpremise" in tipos_set:
            score += 1
        if tipos_set.intersection(TIPOS_NEGATIVOS):
            score -= 1

        # Regra dura: rejeita explicitamente padrões de habitação popular/comercial.
        if any(chave in texto for chave in ["minha casa minha vida", "mcmv", "comercial", "edifício comercial"]):
            return False

        return score >= 2


def salvar_csv(caminho: str, dados: list[CondoResult]) -> None:
    with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=[
                "Nome do Condomínio",
                "Cidade",
                "Endereço Completo",
                "Latitude",
                "Longitude",
            ],
        )
        writer.writeheader()

        for item in dados:
            writer.writerow(
                {
                    "Nome do Condomínio": item.nome,
                    "Cidade": item.cidade,
                    "Endereço Completo": item.endereco,
                    "Latitude": item.latitude if item.latitude is not None else "",
                    "Longitude": item.longitude if item.longitude is not None else "",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mapeia condomínios horizontais e exporta latitude/longitude em CSV."
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        help="Chave da Google Places API. Também pode vir da env GOOGLE_MAPS_API_KEY.",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=CIDADES_PADRAO,
        help="Lista de cidades alvo (separadas por espaço).",
    )
    parser.add_argument(
        "--terms",
        nargs="+",
        default=TERMOS_BUSCA_PADRAO,
        help="Lista de termos de busca (separados por espaço).",
    )
    parser.add_argument(
        "--output",
        default="condominios_alto_padrao.csv",
        help="Caminho do CSV de saída.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Pausa entre paginações da API para estabilizar coleta.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nível de log no terminal.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")

    if not args.api_key:
        raise SystemExit(
            "API key ausente. Use --api-key SUA_CHAVE ou defina GOOGLE_MAPS_API_KEY no ambiente."
        )

    crawler = CondoCrawler(api_key=args.api_key, pause_seconds=args.pause_seconds)
    resultados = crawler.buscar(cidades=args.cities, termos=args.terms)

    salvar_csv(args.output, resultados)
    logging.info("Concluído: %d registros salvos em %s", len(resultados), args.output)


if __name__ == "__main__":
    main()
