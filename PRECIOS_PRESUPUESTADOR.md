# PRECIOS DEL PRESUPUESTADOR PMD - FUENTE DE DATOS

## 1. PRECIOS BASE POR M² (Líneas de calidad)

```javascript
LINEA_BASE = {
  'Línea Confort':         1100,  // USD 1000-1200/m²
  'Línea Premium':         1400,  // USD 1200-1600/m²
  'Línea Alta Gama':       2250,  // USD 2000-2500/m²
  'Línea Lujo Importado':  3800,  // USD 2600-5000/m²
}
```

**FUENTE:** Precio promedio mercado construcción Argentina 2024-2025
**APLICACIÓN:** 
- Modo RÁPIDO: usuario elige calidad directamente
- Modo AVANZADO: base fija USD 1100/m² (Confort), usuario arma su calidad con cada detalle

---

## 2. SISTEMA CONSTRUCTIVO (Multiplicadores)

```javascript
SISTEMAS = {
  'Steel framing':        1.0,   // Base (sin modificador)
  'Mampostería tradicional': 0.95,  // 5% más barato
  'Ladrillo portante':    0.92,   // 8% más barato
  'Troncos/Madera':       1.15,   // 15% más caro
  'Hormigón':             1.12,   // 12% más caro
  'Mixto':                1.05    // 5% más caro
}
```

**FUENTE:** Relación de costos según sistema
**APLICACIÓN:** Multiplica el precio base según sistema elegido

---

## 3. TIPO DE OBRA (Sin costo adicional, solo para clasificación)

- Casa nueva
- Reforma (deriva a chat)
- Edificio/Industrial (deriva a formulario especial)

---

## 4. SUELO/FUNDACIONES (Extras por m²)

```javascript
SUELO_EXTRAS = {
  'Normal':           0,      // Sin extra
  'Expansivo':       +18,     // +USD 18/m²
  'Arcilloso':       +15,     // +USD 15/m²
  'Nivel freático':  +22      // +USD 22/m²
}
```

**FUENTE:** Costos adicionales de fundaciones especiales
**APLICACIÓN:** Se suma al precio base por m²

---

## 5. ETAPA DE CONSTRUCCIÓN (Sin costo, solo para organización)

- Completa llave en mano
- Solo estructura
- Solo terminaciones

---

## 6. PISOS INTERIORES (Extras por m²)

```javascript
PISOS = {
  'Cemento alisado / microcemento': +18,   // USD/m²
  'Porcelanato nacional':           +25,
  'Porcelanato importado':          +45,
  'Madera ingeniería':              +55,
  'Mármol / Piedra':                +75
}
```

**FUENTE:** Precios mercado materiales + colocación

---

## 7. ABERTURAS (Extras por m²)

```javascript
ABERTURAS = {
  'Aluminio línea modena':    +35,
  'Aluminio DVH':             +55,
  'PVC DVH':                  +65,
  'Madera':                   +48,
  'Aluminio termopanel':      +72
}
```

**FUENTE:** Costo promedio aberturas por m² cubierto

---

## 8. COCINA (Extras fijos en USD)

```javascript
COCINA = {
  'Cocina nacional básica':     3500,
  'Cocina nacional completa':   5800,
  'Cocina importada semi':      8500,
  'Cocina importada completa':  12000
}
```

**FUENTE:** Precios equipamiento + instalación

---

## 9. CLIMATIZACIÓN (Extras por m²)

```javascript
CLIMA = {
  'Sin sistema':              0,
  'Split por ambiente':      +12,
  'VRV / Centralizado':      +25,
  'Piso radiante':           +35,
  'Radiadores':              +22
}
```

**FUENTE:** Costo instalación + equipos

---

## 10. CUBIERTA (USD por m² de cubierta)

```javascript
CUBIERTA = {
  'Chapa simple':             28,   // USD/m² cubierta
  'Teja cerámica':            45,
  'Teja hormigón':            38,
  'Pizarra':                  65,
  'Losa transitable':         55
}
```

**FUENTE:** Costo estructura + material + colocación

---

## 11. REVESTIMIENTO EXTERIOR (Extras por m² de fachada)

```javascript
FACHADA = {
  'Revoque símil piedra':     15,   // USD/m² fachada
  'Placa cementicia':         22,
  'Ladrillo a la vista':      28,
  'Piedra':                   45,
  'Madera':                   38
}
```

**FUENTE:** Costo material + colocación fachada

---

## 12. BAÑOS (Extras por baño)

```javascript
BAÑOS = {
  'Sanitarios nacionales':    850,   // USD por baño
  'Sanitarios ferrum':       1200,
  'Sanitarios importados':   1800,
  'Sanitarios lujo':         2800
}
```

**FUENTE:** Equipamiento + grifería + instalación

---

## 13. AGUA CALIENTE (Extras fijos)

```javascript
AGUA_CALIENTE = {
  'Termotanque eléctrico':    450,
  'Termotanque a gas':        650,
  'Caldera':                  1200,
  'Termotanque solar':        1800
}
```

---

## 14. ELÉCTRICA (Extras fijos)

```javascript
ELECTRICA = {
  'Instalación estándar':     0,
  'Domótica básica':        1500,
  'Domótica completa':      3500
}
```

---

## 15. ENERGÍA SOLAR (Extras fijos)

```javascript
SOLAR = {
  'Sin paneles':              0,
  '2kW residencial':        2500,
  '4kW':                    4200,
  '6kW+':                   6500
}
```

---

## 16. EXTRAS TOGGLEABLES

### Pileta
- **Modo metros**: +USD 15,000 fijo
- **Modo ambientes**: +USD 10,000 fijo

### Ambientes (modo ambientes)
- Habitación: 18.4m² (16m² + 15% circulación)
- Baño: 6.9m² (6m² + 15%)
- Living: 70m² (promedio 60-80m²)
- Cocina: 16m²
- Lavadero: 7.5m²
- Hab. servicio: 12m²
- Garage: 24m²/auto

---

## 17. MULTIPLICADOR POR PLANTAS

```javascript
PLANTAS = {
  1: 1.0,    // 100%
  2: 1.6,    // PB 100% + PA 60% = 160%
  3: 2.05    // PB 100% + PA1 60% + PA2 45% = 205%
}
```

**FUENTE:** Relación costo/área según nivel
- Planta baja: 100% (cimientos, estructura completa)
- Planta alta: 60% (sin cimientos, escalera)
- 2da planta alta: 45% (estructura reducida)

---

## CÁLCULO FINAL

```javascript
precio_final = (
  base_USD_m² 
  * sistema_multiplicador 
  * plantas_multiplicador
  + suelo_extra_por_m²
  + pisos_extra_por_m²
  + aberturas_extra_por_m²
  + clima_extra_por_m²
  + cubierta_USD_por_m²_cubierta
  + fachada_USD_por_m²_fachada
  + baños_extra_por_baño
) * m²_totales
+ cocina_fijo
+ agua_caliente_fijo
+ eléctrica_fijo
+ solar_fijo
+ pileta_fijo (si aplica)
```

---

## FUENTES DE INFORMACIÓN

1. **Precios base**: Promedio mercado construcción AMBA 2024-2025
2. **Materiales**: Precios actualizados proveedores (Holcim, Aluar, FV, etc.)
3. **Mano de obra**: Relación real mercado informal Nordelta/Tigre/San Isidro
   - Oficial: USD 100K ARS/día
   - Ayudante: USD 70K ARS/día
4. **Referencias**: ARQ Clarín, publicaciones sector construcción
5. **Ajustes**: Multiplicadores probados en 50+ obras PMD desde 2014

---

## NOTAS

- Todos los precios en USD para evitar inflación
- Spread ±10-12% según calidad materiales elegidos
- Precio incluye: materiales + mano obra + honorarios + imprevistos (5%)
- NO incluye: terreno, escrituración, mudanza, decoración
