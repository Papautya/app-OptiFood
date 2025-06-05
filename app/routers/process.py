# app/routers/process.py

import os
import json
import re
from fastapi import APIRouter, HTTPException
from app.models import WasteInput, CombinedOutput
from app.data import load_historical_data
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Instancia el cliente
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()

@router.post("/process", response_model=CombinedOutput)
def process_waste_and_predict(data: WasteInput):
    # ——— 0. Carga y filtra histórico desde tu CSV ———
    df = load_historical_data()  # DataFrame en que Country debe ser "Colombia"
    hist_df = df[
        (df["Country"].str.lower() == "colombia") &
        (df["Food Category"].str.lower() == data.category.lower())
    ]
    hist_list = hist_df[
        ["Year", "Total Waste (Tons)", "Economic Loss (Million $)"]
    ].to_dict(orient="records")
    hist_json = json.dumps(hist_list)

    # ——— 1. Cálculo de métricas ———
    waste_pct = data.wasted_tons / data.purchased_tons * 100
    econ_loss = data.total_value * data.wasted_tons / data.purchased_tons
    loss_per_ton = econ_loss / data.wasted_tons
    sales_ratio = (
        data.sales_volume / data.wasted_tons
        if data.sales_volume is not None
        else None
    )

    # Formateo del ratio
    sales_ratio_str = f"{sales_ratio:.2f}" if sales_ratio is not None else "no calculado"

    # ——— 2. Prompts para OpenAI ———
    system_prompt = """
Eres un **Analista Senior de Gestión de Desperdicios en Colombia**. Tienes formación en Lean Manufacturing, Six Sigma y Economía Circular, y tu enfoque es **colaborativo** y **dinámico**. 
Tus objetivos son:
1. **Diagnóstico inmediato**  
   - Señalar las razones principales de un % de desperdicio tan alto (p. ej. 60 %: causas en temperatura, lead time, rotación, embalaje).  
2. **Detectar huecos de información**  
   - Si falta algo crítico para profundizar (variabilidad de demanda, embalaje, capacidad de bodega, personal), pregunta **hasta 3 veces** de manera concreta antes de continuar.  
3. **Recomendaciones escalonadas**  
   - Propón **quick wins** (acciones a < 1 mes), **medio plazo** (1–3 meses) y **largo plazo** (> 3 meses).  
   - Para cada acción incluye:  
     • **action** (qué hacer)  
     • **responsible** (quién)  
     • **deadline_days** (plazo en días)  
     • **kpi_target** (qué métrica mejorar)  
     • **estimated_savings_cop** (ahorro anual estimado en COP)  
4. **Predicción de pedido óptimo**  
   - Basada en histórico de Colombia, lead times y estacionalidad.  
   - Devuelve **recommended_order_tons**, **min_order_tons** (–10 %) y **max_order_tons** (+10 %).  
5. **Plan de acción dinámico**  
   - Si el usuario responde tus preguntas, ajusta tu plan inmediatamente en la misma conversación.

**Tono:** profesional, colaborativo y orientado a resultados.  
Responde siempre en un **único bloque JSON**.
"""

    extra = f"\nContexto adicional: {data.additional_context}" if getattr(data, "additional_context", None) else ""

    user_prompt = (
        f"**Contexto inicial**:\n"
        f"- País: Colombia (COP, toneladas métricas)\n"
        f"- Categoría: {data.category}\n"
        f"- Compradas: {data.purchased_tons} t\n"
        f"- Desperdiciadas: {data.wasted_tons} t ({waste_pct:.2f} %)\n"
        f"- Valor compra: {data.total_value:,} COP\n"
        f"- Ventas: {data.sales_volume or 'N/A'} COP\n"
        f"- Lead time: {getattr(data, 'lead_time_days', 'N/A')} días\n"
        f"- Frecuencia de pedido: {getattr(data, 'order_frequency', 'N/A')}\n"
        f"- Almacenaje: {data.storage_temperature or 'N/A'} °C; rotación {data.rotation_method}\n"
        f"- Vida útil: {getattr(data, 'shelf_life_days', 'N/A')} días"
        f"{extra}\n\n"
        f"**Histórico relevante (Colombia)**:\n{hist_json}\n\n"
        f"**Métricas base**:\n"
        f"* % desperdicio: {waste_pct:.2f}%\n"
        f"* Pérdida económica: {econ_loss:,.0f} COP\n"
        f"* Pérdida/ton: {loss_per_ton:,.0f} COP/t\n"
        f"* Ratio ventas/desperdicio: {sales_ratio_str}\n\n"
        "**Pasos a seguir:**\n"
        "1. Realiza un diagnóstico rápido de las causas principales.\n"
        "2. Formula preguntas si te hace falta información.\n"
        "3. Cuando tengas todo, entrega el JSON con quick wins, mid_term, long_term y predicción.\n"
        "\n**RESPONDE:** sólo JSON, sin texto extra.\n"
        "```json\n"
        "{\n"
        "  \"waste_percentage\": <float>,\n"
        "  \"economic_loss\": <float>,\n"
        "  \"loss_per_ton\": <float>,\n"
        "  \"sales_to_waste_ratio\": <float|null>,\n"
        "  \"root_causes\": [\"<str>\", …],\n"
        "  \"quick_wins\": [\n"
        "    {\"action\":<str>,\"responsible\":<str>,\"deadline_days\":<int>,"
             "\"kpi_target\":<str>,\"estimated_savings_cop\":<float>}, …\n"
        "  ],\n"
        "  \"mid_term\": [ {...}, … ],\n"
        "  \"long_term\": [ {...}, … ],\n"
        "  \"recommended_order_tons\": <float>,\n"
        "  \"min_order_tons\": <float>,\n"
        "  \"max_order_tons\": <float>,\n"
        "  \"prediction_explanation\": \"<str>\"\n"
        "}\n"
        "```"
    )

    # ——— 3. Llamada a OpenAI ———
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al invocar OpenAI: {e}")

    # ——— 4. Limpieza de fences de Markdown ———
    raw_clean = re.sub(r"^```(?:json)?\s*", "", raw)
    raw_clean = re.sub(r"\s*```$", "", raw_clean).strip()

    # ——— 5. Parseo del JSON ———
    try:
        parsed = json.loads(raw_clean)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI no devolvió un JSON válido. Contenido limpio:\n{raw_clean}"
        )

    # ——— 6. Retorno tipado ———
    return CombinedOutput(**parsed)
