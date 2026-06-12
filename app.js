const data = window.BIWENGER_DASHBOARD_DATA;

const palette = ["#006d77", "#6d597a", "#b56576", "#2a9d8f", "#457b9d", "#b56576", "#e9c46a"];
const teamColors = new Map(
  [
    ["Arregui", "#006d77"],
    ["CD Cornisa Azul", "#6d597a"],
    ["Julia", "#b56576"],
    ["Karlox F.C.", "#2a9d8f"],
    ["Los vengadores", "#457b9d"],
    ["Ricardo J", "#e29578"],
    ["V\u00edctor Orta", "#e9c46a"],
  ].map(([name, color]) => [teamKey(name), color]),
);
const teamImages = new Map(
  [
    ["Los vengadores", "assets/team-icons/vengadores.png"],
    ["Karlox F.C.", "assets/team-icons/karlox.png"],
    ["Arregui", "assets/team-icons/arregui.png"],
    ["Ricardo J", "assets/team-icons/ricardo.svg"],
    ["V\u00edctor Orta", "assets/team-icons/ignacio.webp"],
    ["CD Cornisa Azul", "assets/team-icons/alfonso.avif"],
    ["Julia", "assets/team-icons/julia.jpg"],
  ].map(([name, path]) => [teamKey(name), path]),
);
const positionColors = new Map([
  ["Portería", "#006d77"],
  ["Defensa", "#457b9d"],
  ["Centro del campo", "#e9c46a"],
  ["Delantera", "#b56576"],
  ["Entrenador", "#6d597a"],
  ["Sin posición", "#667789"],
]);
const positionOrder = ["Portería", "Defensa", "Centro del campo", "Delantera", "Entrenador", "Sin posición"];

const baseLayout = {
  margin: { l: 64, r: 24, t: 24, b: 68 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, system-ui, sans-serif", color: "#15212f" },
  hoverlabel: { bgcolor: "#15212f", font: { color: "white" } },
  dragmode: false,
  xaxis: { fixedrange: true, gridcolor: "#dfe7ee", zerolinecolor: "#cfd9e3" },
  yaxis: { fixedrange: true, gridcolor: "#dfe7ee", zerolinecolor: "#cfd9e3" },
};

const config = {
  responsive: true,
  displayModeBar: false,
  scrollZoom: false,
  doubleClick: false,
  showTips: false,
};

const fmt = new Intl.NumberFormat("es-ES");
const pct = new Intl.NumberFormat("es-ES", { style: "percent", maximumFractionDigits: 1 });
const money = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });

function byValue(rows, key, desc = true) {
  return [...rows].sort((a, b) => (desc ? b[key] - a[key] : a[key] - b[key]));
}

function teamColor(name) {
  const fixed = teamColors.get(teamKey(name));
  if (fixed) return fixed;
  const idx = data.teams.findIndex((team) => team.user_name === name);
  return palette[(idx < 0 ? 0 : idx) % palette.length];
}

function teamKey(name) {
  return String(name || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function teamImage(name) {
  return teamImages.get(teamKey(name)) || "";
}

function rowForTeam(rows, teamName) {
  return rows?.find((row) => teamKey(row.user_name) === teamKey(teamName)) || {};
}

function imageForChart(name, x, y, options = {}) {
  const source = teamImage(name);
  if (!source) return null;
  return {
    source,
    xref: "x",
    yref: "y",
    x,
    y,
    sizex: options.sizex ?? 24,
    sizey: options.sizey ?? 0.65,
    xanchor: options.xanchor ?? "center",
    yanchor: options.yanchor ?? "middle",
    sizing: "contain",
    layer: "above",
  };
}

function horizontalAxisImages(rows, yKey, maxValue, imageX) {
  const imageWidth = maxValue <= 1 ? maxValue * 0.07 : Math.max(maxValue * 0.06, 0.35);
  return rows
    .map((row) =>
      imageForChart(row.user_name || row[yKey], imageX, row[yKey], {
        sizex: imageWidth,
        sizey: 0.72,
        xanchor: "center",
      }),
    )
    .filter(Boolean);
}

function verticalTopImages(rows, xKey, yKey, maxValue) {
  return rows
    .map((row) =>
      imageForChart(row.user_name || row[xKey], row[xKey], -maxValue * 0.08, {
        sizex: 0.52,
        sizey: Math.max(maxValue * 0.12, 1),
      }),
    )
    .filter(Boolean);
}

function renderScoreboard() {
  const el = document.getElementById("scoreboard");
  el.innerHTML = data.latest_standings
    .map(
      (row) => `
        <article class="team-tile">
          <div class="tile-top">
            <img class="team-avatar" src="${teamImage(row.user_name)}" alt="" loading="lazy" />
            <span class="rank">${row.league_position}</span>
          </div>
          <h2>${row.user_name}</h2>
          <p>${fmt.format(row.total_points_after_round)} pts · ${money.format(row.team_value)} €</p>
        </article>
      `,
    )
    .join("");
}

function makeBar(id, rows, xKey, yKey, options = {}) {
  const sorted = options.ascending ? byValue(rows, xKey, false) : byValue(rows, xKey, true);
  const maxValue = Math.max(...sorted.map((row) => Math.abs(row[xKey] || 0)), 1);
  const minValue = Math.min(...sorted.map((row) => row[xKey] || 0), 0);
  const imageX = minValue < 0 ? minValue - maxValue * 0.08 : -maxValue * 0.07;
  const leftRange = minValue < 0 ? minValue - maxValue * 0.18 : -maxValue * 0.16;
  Plotly.newPlot(
    id,
    [
      {
        type: "bar",
        orientation: "h",
        x: sorted.map((row) => row[xKey]),
        y: sorted.map((row) => row[yKey]),
        marker: { color: sorted.map((row) => teamColor(row.user_name || row[yKey])) },
        text: sorted.map((row) => options.format ? options.format(row[xKey], row) : row[xKey]),
        textposition: "auto",
        hovertemplate: options.hover || "%{y}<br>%{x}<extra></extra>",
      },
    ],
    {
      ...baseLayout,
      height: options.height || 380,
      margin: { l: 164, r: 24, t: 18, b: 44 },
      images: options.logos === false ? [] : horizontalAxisImages(sorted, yKey, maxValue, imageX),
      xaxis: {
        ...baseLayout.xaxis,
        title: options.xTitle || "",
        range: options.xRange || [leftRange, maxValue * 1.18],
      },
      yaxis: { ...baseLayout.yaxis, autorange: "reversed" },
    },
    config,
  );
}

function renderPositions() {
  const rounds = [...new Set(data.position_progress.map((row) => row.round_order))].sort((a, b) => a - b);
  const maxPoints = Math.max(...data.position_progress.map((row) => row.total_points_after_round || 0));
  const teams = data.teams.map((team) => team.user_name);

  function rowsForRound(round) {
    return data.position_progress
      .filter((row) => row.round_order === round)
      .sort((a, b) => a.total_points_after_round - b.total_points_after_round);
  }

  function roundTitle(round) {
    return rowsForRound(round)[0]?.round_name || `Jornada ${round}`;
  }

  function rankForRound(round) {
    const rows = rowsForRound(round);
    return new Map(rows.map((row, index) => [row.user_name, { ...row, y: index + 1 }]));
  }

  function titleAnnotation(round) {
    return {
      text: `<b>${roundTitle(round)}</b>`,
      x: 1,
      y: 1.15,
      xref: "paper",
      yref: "paper",
      xanchor: "right",
      yanchor: "bottom",
      showarrow: false,
      font: { size: 18, color: "#15212f" },
    };
  }

  function imageLayer(round) {
    const iconSizeX = maxPoints * 0.055;
    return rowsForRound(round)
      .map((row, index) => ({
        source: teamImage(row.user_name),
        xref: "x",
        yref: "y",
        x: -maxPoints * 0.085,
        y: index + 1,
        sizex: iconSizeX,
        sizey: 0.62,
        xanchor: "center",
        yanchor: "middle",
        sizing: "contain",
        layer: "above",
      }))
      .filter((image) => image.source);
  }

  function teamAxisAnnotations(round) {
    return rowsForRound(round).map((row, index) => ({
      text: `<b>${row.user_name}</b>`,
      x: -maxPoints * 0.05,
      y: index + 1,
      xref: "x",
      yref: "y",
      xanchor: "left",
      yanchor: "middle",
      showarrow: false,
      font: { size: 13, color: "#15212f" },
    }));
  }

  function traceForTeam(team, round) {
    const row = rankForRound(round).get(team);
    return {
      type: "bar",
      orientation: "h",
      name: team,
      x: [row?.total_points_after_round || 0],
      y: [row?.y || 0],
      width: [0.72],
      marker: { color: teamColor(team) },
      text: [`${team} · ${fmt.format(row?.total_points_after_round || 0)} pts`],
      textposition: "outside",
      cliponaxis: false,
      customdata: [[roundTitle(round), row?.lineup_points || 0, row?.league_position || ""]],
      hovertemplate:
        `${team}<br>%{customdata[0]}<br>Total: %{x} pts<br>Jornada: %{customdata[1]} pts<br>Posición: %{customdata[2]}<extra></extra>`,
    };
  }

  const frames = rounds.map((round) => ({
    name: String(round),
    data: teams.map((team) => traceForTeam(team, round)),
    layout: {
      annotations: [titleAnnotation(round), ...teamAxisAnnotations(round)],
      images: imageLayer(round),
    },
  }));

  Plotly.newPlot(
    "positionsChart",
    teams.map((team) => traceForTeam(team, rounds[0])),
    {
      ...baseLayout,
      height: 620,
      margin: { l: 118, r: 150, t: 94, b: 78 },
      annotations: [titleAnnotation(rounds[0]), ...teamAxisAnnotations(rounds[0])],
      images: imageLayer(rounds[0]),
      bargap: 0.25,
      yaxis: {
        ...baseLayout.yaxis,
        title: "",
        range: [0.35, data.teams.length + 0.8],
        showticklabels: false,
        showgrid: false,
        zeroline: false,
      },
      xaxis: {
        ...baseLayout.xaxis,
        title: "Puntos totales",
        range: [-maxPoints * 0.18, maxPoints * 1.15],
        zeroline: false,
      },
      showlegend: false,
      updatemenus: [
        {
          type: "buttons",
          direction: "left",
          x: 0,
          y: 1.16,
          xanchor: "left",
          yanchor: "top",
          buttons: [
            {
              label: "Play",
              method: "animate",
              args: [
                null,
                {
                  frame: { duration: 520, redraw: true },
                  transition: { duration: 420, easing: "cubic-in-out" },
                  fromcurrent: true,
                },
              ],
            },
            {
              label: "Pause",
              method: "animate",
              args: [[null], { frame: { duration: 0 }, mode: "immediate", transition: { duration: 0 } }],
            },
          ],
        },
      ],
      sliders: [
        {
          active: 0,
          y: -0.06,
          steps: rounds.map((round) => ({
            label: String(round),
            method: "animate",
            args: [
              [String(round)],
              { mode: "immediate", frame: { duration: 0, redraw: true }, transition: { duration: 0 } },
            ],
          })),
        },
      ],
    },
    config,
  ).then(() => Plotly.addFrames("positionsChart", frames));
}

function renderWinsLosses() {
  const rows = byValue(data.round_counts, "jornadas_ganadas", true);
  const topRows = rows.map((row) => ({
    user_name: row.user_name,
    chart_top: Math.max(row.jornadas_ganadas || 0, row.jornadas_perdidas || 0),
  }));
  const maxRoundCount = Math.max(...topRows.map((row) => row.chart_top), 1);
  Plotly.newPlot(
    "winsLossesChart",
    [
      {
        type: "bar",
        name: "Ganadas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.jornadas_ganadas),
        marker: { color: "#2a9d8f" },
      },
      {
        type: "bar",
        name: "Perdidas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.jornadas_perdidas),
        marker: { color: "#e29578" },
      },
    ],
    {
      ...baseLayout,
      barmode: "group",
      height: 380,
      images: verticalTopImages(topRows, "user_name", "chart_top", maxRoundCount),
      yaxis: { ...baseLayout.yaxis, title: "Jornadas", range: [-maxRoundCount * 0.2, maxRoundCount * 1.16] },
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      legend: { orientation: "h" },
    },
    config,
  );
}

function renderGoalCharts() {
  makeBar("goalsChart", data.team_goals, "goles", "user_name", {
    xTitle: "Goles alineados",
    format: (value) => fmt.format(value),
  });

  const goalRows = byValue(data.goal_dependence, "share", true);
  Plotly.newPlot(
    "goalDependenceChart",
    [
      {
        type: "bar",
        orientation: "h",
        x: goalRows.map((row) => row.share),
        y: goalRows.map((row) => row.user_name),
        text: goalRows.map((row) => `${row.player_name} · ${pct.format(row.share)}`),
        customdata: goalRows.map((row) => [row.player_name, row.player_goals, row.goles]),
        hovertemplate: "%{y}<br>%{customdata[0]}: %{customdata[1]} de %{customdata[2]} goles<extra></extra>",
        marker: { color: goalRows.map((row) => teamColor(row.user_name)) },
      },
    ],
    {
      ...baseLayout,
      height: 380,
      margin: { l: 132, r: 24, t: 18, b: 44 },
      xaxis: { ...baseLayout.xaxis, tickformat: ".0%", title: "Peso del máximo goleador" },
      yaxis: { ...baseLayout.yaxis, autorange: "reversed" },
    },
    config,
  );

  const pointRows = byValue(data.point_dependence, "share", true);
  Plotly.newPlot(
    "pointDependenceChart",
    [
      {
        type: "bar",
        orientation: "h",
        x: pointRows.map((row) => row.share),
        y: pointRows.map((row) => row.user_name),
        text: pointRows.map((row) => `${row.player_name} · ${pct.format(row.share)}`),
        customdata: pointRows.map((row) => [row.player_name, row.player_points, row.total_player_points]),
        hovertemplate: "%{y}<br>%{customdata[0]}: %{customdata[1]} de %{customdata[2]} pts cubiertos<extra></extra>",
        marker: { color: pointRows.map((row) => teamColor(row.user_name)) },
      },
    ],
    {
      ...baseLayout,
      height: 380,
      margin: { l: 132, r: 24, t: 18, b: 44 },
      xaxis: { ...baseLayout.xaxis, tickformat: ".0%", title: "Peso del jugador más decisivo" },
      yaxis: { ...baseLayout.yaxis, autorange: "reversed" },
    },
    config,
  );
}

function renderPositionCharts() {
  const rows = data.position_summary || [];
  const teams = data.teams.map((team) => team.user_name);
  const positions = positionOrder.filter((position) => rows.some((row) => row.position_name === position));
  const traces = positions.map((position) => {
    const positionRows = teams.map((team) => rowForTeam(rows.filter((row) => row.position_name === position), team));
    return {
      type: "bar",
      name: position,
      x: teams,
      y: positionRows.map((row) => row.position_points || 0),
      marker: { color: positionColors.get(position) || "#667789" },
      customdata: positionRows.map((row) => [row.players_used || 0, row.position_goals || 0, row.point_share || 0]),
      hovertemplate:
        "%{x}<br>" +
        position +
        ": %{y:.0f} pts<br>Jugadores: %{customdata[0]}<br>Goles: %{customdata[1]}<br>Peso: %{customdata[2]:.1%}<extra></extra>",
    };
  });
  Plotly.newPlot(
    "positionPointsChart",
    traces,
    {
      ...baseLayout,
      barmode: "group",
      height: 430,
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      yaxis: { ...baseLayout.yaxis, title: "Puntos cubiertos" },
      legend: { orientation: "h", y: 1.14 },
    },
    config,
  );

  Plotly.newPlot(
    "positionDependenceChart",
    positions.map((position) => {
      const positionRows = teams.map((team) => rowForTeam(rows.filter((row) => row.position_name === position), team));
      return {
        type: "bar",
        name: position,
        x: teams,
        y: positionRows.map((row) => row.point_share || 0),
        marker: { color: positionColors.get(position) || "#667789" },
        customdata: positionRows.map((row) => [row.position_points || 0, row.total_player_points || 0]),
        hovertemplate:
          "%{x}<br>" +
          position +
          ": %{y:.1%}<br>Puntos de la línea: %{customdata[0]:.0f}<br>Total cubierto: %{customdata[1]:.0f}<extra></extra>",
      };
    }),
    {
      ...baseLayout,
      barmode: "group",
      height: 430,
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      yaxis: { ...baseLayout.yaxis, title: "Peso sobre puntos cubiertos", tickformat: ".0%" },
      legend: { orientation: "h", y: 1.14 },
    },
    config,
  );
}

function renderDiscipline() {
  const maxPalos = Math.max(...data.discipline.map((row) => row.palos_index || 0), 1);
  Plotly.newPlot(
    "disciplineChart",
    [
      {
        type: "bar",
        x: data.discipline.map((row) => row.user_name),
        y: data.discipline.map((row) => row.palos_index),
        marker: { color: data.discipline.map((row) => teamColor(row.user_name)) },
        customdata: data.discipline.map((row) => [row.amarillas, row.rojas, row.segundas_amarillas]),
        hovertemplate:
          "%{x}<br>Índice: %{y}<br>Amarillas efectivas: %{customdata[0]}<br>Rojas efectivas: %{customdata[1]}<br>Dobles amarillas: %{customdata[2]}<extra></extra>",
      },
    ],
    {
      ...baseLayout,
      height: 380,
      images: verticalTopImages(data.discipline, "user_name", "palos_index", maxPalos),
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      yaxis: { ...baseLayout.yaxis, title: "Índice parcial", range: [-maxPalos * 0.2, maxPalos * 1.16] },
    },
    config,
  );
}

function renderMarket() {
  makeBar("profitChart", data.trade_summary, "beneficio_bruto", "user_name", {
    xTitle: "Beneficio bruto reconstruido (€)",
    format: (value) => `${money.format(value)} €`,
    hover: "%{y}<br>%{x:,.0f} €<extra></extra>",
  });

  makeBar("roiChart", data.trade_summary, "rentabilidad", "user_name", {
    xTitle: "Rentabilidad",
    format: (value) => pct.format(value),
    hover: "%{y}<br>%{x:.1%}<extra></extra>",
  });

  makeBar("signingPointsChart", data.signing_points, "puntos_por_fichajes", "user_name", {
    xTitle: "Puntos desde fichajes",
    format: (value) => fmt.format(value),
  });

  makeBar("firstRoundSigningChart", data.first_round_signing_points, "puntos_primera_jornada_fichaje", "user_name", {
    xTitle: "Puntos en primera jornada tras fichar",
    format: (value) => fmt.format(value),
  });

  renderTradingActivityChart();
  renderMarketVolumeChart();
}

function renderTradingActivityChart() {
  const rows = byValue(data.trade_summary, "operaciones_cerradas", true);
  const maxOps = Math.max(...rows.map((row) => row.operaciones_cerradas || 0), 1);
  const maxDays = Math.max(...rows.map((row) => row.dias_medio || 0), 1);
  Plotly.newPlot(
    "tradingActivityChart",
    [
      {
        type: "bar",
        name: "Compraventas cerradas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.operaciones_cerradas),
        marker: { color: rows.map((row) => teamColor(row.user_name)) },
        customdata: rows.map((row) => [row.dias_medio, row.beneficio_bruto, row.rentabilidad]),
        hovertemplate:
          "%{x}<br>Operaciones cerradas: %{y}<br>Días medios: %{customdata[0]:.1f}<br>Beneficio: %{customdata[1]:,.0f} €<br>ROI: %{customdata[2]:.1%}<extra></extra>",
      },
      {
        type: "scatter",
        mode: "lines+markers",
        name: "Días medios",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.dias_medio),
        yaxis: "y2",
        line: { color: "#15212f", width: 3, shape: "spline" },
        marker: { color: "#15212f", size: 9, line: { color: "#ffffff", width: 2 } },
        hovertemplate: "%{x}<br>Días medios entre compra y venta: %{y:.1f}<extra></extra>",
      },
    ],
    {
      ...baseLayout,
      height: 380,
      images: verticalTopImages(
        rows.map((row) => ({ ...row, chart_top: row.operaciones_cerradas || 0 })),
        "user_name",
        "chart_top",
        maxOps,
      ),
      margin: { l: 56, r: 64, t: 20, b: 88 },
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      yaxis: {
        ...baseLayout.yaxis,
        title: "Compraventas cerradas",
        range: [-maxOps * 0.22, maxOps * 1.18],
      },
      yaxis2: {
        title: "Días medios",
        overlaying: "y",
        side: "right",
        fixedrange: true,
        range: [0, maxDays * 1.22],
        showgrid: false,
        zeroline: false,
      },
      legend: { orientation: "h", y: 1.12 },
    },
    config,
  );
}

function renderMarketVolumeChart() {
  const rows = byValue(data.market_activity_summary || [], "movimientos_visibles", true);
  const maxVolume = Math.max(...rows.map((row) => row.movimientos_visibles || 0), 1);
  Plotly.newPlot(
    "marketVolumeChart",
    [
      {
        type: "bar",
        name: "Compras visibles",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.compras_visibles),
        marker: { color: "#006d77" },
        hovertemplate: "%{x}<br>Compras visibles: %{y}<extra></extra>",
      },
      {
        type: "bar",
        name: "Ventas estimadas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.ventas_totales_estimadas),
        marker: { color: "#e9c46a" },
        customdata: rows.map((row) => [row.ventas_publicadas || 0, row.ventas_inferidas_sin_publicacion || 0]),
        hovertemplate:
          "%{x}<br>Ventas estimadas: %{y}<br>Publicadas: %{customdata[0]}<br>Inferidas sin publicación: %{customdata[1]}<extra></extra>",
      },
    ],
    {
      ...baseLayout,
      barmode: "group",
      height: 380,
      images: verticalTopImages(
        rows.map((row) => ({ ...row, chart_top: row.movimientos_visibles || 0 })),
        "user_name",
        "chart_top",
        maxVolume,
      ),
      yaxis: { ...baseLayout.yaxis, title: "Movimientos", range: [-maxVolume * 0.2, maxVolume * 1.18] },
      xaxis: { ...baseLayout.xaxis, tickangle: -28 },
      legend: { orientation: "h", y: 1.12 },
    },
    config,
  );
}

function renderManagement() {
  makeBar("loyaltyChart", data.loyalty, "rondas_medias_por_jugador", "user_name", {
    xTitle: "Rondas alineadas de media por jugador",
    format: (value) => value.toFixed(2),
  });

  makeBar("concentrationChart", data.concentration, "concentracion_hhi", "user_name", {
    xTitle: "HHI de puntos por jugador",
    format: (value) => value.toFixed(3),
  });

  makeBar("valueChart", data.value_efficiency, "puntos_por_millon", "user_name", {
    xTitle: "Puntos por millón de valor",
    format: (value) => value.toFixed(2),
  });

  makeBar("volatilityChart", data.volatility, "regularidad_std", "user_name", {
    ascending: true,
    xTitle: "Desviación típica de puntos de jornada",
    format: (value) => value.toFixed(2),
  });
}

function renderTables() {
  renderTable("tradesTable", data.completed_trades.slice(0, 12), [
    ["user_name", "Equipo"],
    ["player_name", "Jugador"],
    ["buy_amount", "Compra", (v) => `${money.format(v)} €`],
    ["sell_amount", "Venta", (v) => `${money.format(v)} €`],
    ["profit", "Beneficio", (v) => `${money.format(v)} €`],
    ["roi", "ROI", (v) => pct.format(v)],
  ]);

  renderTable("signingsTable", data.top_signings.slice(0, 12), [
    ["user_name", "Equipo"],
    ["player_name", "Jugador"],
    ["points_after_signing", "Puntos", (v) => fmt.format(v)],
    ["rounds_after_signing", "Jornadas", (v) => fmt.format(v)],
  ]);
}

function renderTable(id, rows, columns) {
  const el = document.getElementById(id);
  if (!rows || rows.length === 0) {
    el.innerHTML = "<tbody><tr><td>No hay datos suficientes</td></tr></tbody>";
    return;
  }
  const head = `<thead><tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead>`;
  const body = rows
    .map(
      (row) =>
        `<tr>${columns
          .map(([key, , formatter]) => {
            const value = row[key];
            return `<td>${formatter ? formatter(value, row) : value ?? ""}</td>`;
          })
          .join("")}</tr>`,
    )
    .join("");
  el.innerHTML = `${head}<tbody>${body}</tbody>`;
}

function metricValue(rows, teamName, key) {
  const row = rowForTeam(rows, teamName);
  return Number(row[key] ?? 0);
}

function rankLabel(rows, teamName, key, descending = true) {
  const sorted = [...(rows || [])].sort((a, b) => (descending ? b[key] - a[key] : a[key] - b[key]));
  const index = sorted.findIndex((row) => teamKey(row.user_name) === teamKey(teamName));
  return index < 0 ? "-" : `${index + 1}/${sorted.length}`;
}

function teamProfileText(teamName) {
  const trades = metricValue(data.market_activity_summary, teamName, "movimientos_visibles");
  const loyalty = metricValue(data.loyalty, teamName, "rondas_medias_por_jugador");
  const concentration = metricValue(data.concentration, teamName, "concentracion_hhi");
  const palos = metricValue(data.discipline, teamName, "palos_index");
  const tradeMedian = byValue(data.market_activity_summary || [], "movimientos_visibles", true)[Math.floor((data.market_activity_summary || []).length / 2)]?.movimientos_visibles || 0;
  const loyaltyMedian = byValue(data.loyalty || [], "rondas_medias_por_jugador", true)[Math.floor((data.loyalty || []).length / 2)]?.rondas_medias_por_jugador || 0;
  const concentrationMedian = byValue(data.concentration || [], "concentracion_hhi", true)[Math.floor((data.concentration || []).length / 2)]?.concentracion_hhi || 0;
  const palosMedian = byValue(data.discipline || [], "palos_index", true)[Math.floor((data.discipline || []).length / 2)]?.palos_index || 0;
  const traits = [];
  traits.push(trades >= tradeMedian ? "mercado inquieto" : "plantilla más tranquila");
  traits.push(loyalty >= loyaltyMedian ? "bloque estable" : "rotación alta");
  traits.push(concentration >= concentrationMedian ? "puntos concentrados" : "reparto coral");
  traits.push(palos >= palosMedian ? "ritmo intenso" : "perfil limpio");
  return `Perfil: ${traits.join(", ")}.`;
}

function awardRows(teamName) {
  const definitions = [
    ["latest_standings", "league_position", false, "Campeón de la general", "Cierra la general", (v) => `Puesto ${v}`],
    ["round_counts", "jornadas_ganadas", true, "Más jornadas ganadas", "Menos jornadas ganadas", (v) => `${fmt.format(v)} jornadas`],
    ["round_counts", "jornadas_perdidas", true, "Más farolillos de jornada", "Menos farolillos de jornada", (v) => `${fmt.format(v)} jornadas`],
    ["team_goals", "goles", true, "Más goles alineados", "Menos goles alineados", (v) => `${fmt.format(v)} goles`],
    ["goal_dependence", "share", true, "Mayor dependencia goleadora", "Menor dependencia goleadora", (v) => pct.format(v)],
    ["point_dependence", "share", true, "Mayor dependencia de un jugador", "Menor dependencia de un jugador", (v) => pct.format(v)],
    ["discipline", "palos_index", true, "Índice de palos más alto", "Índice de palos más bajo", (v) => fmt.format(v)],
    ["trade_summary", "beneficio_bruto", true, "Mejor beneficio trading", "Peor beneficio trading", (v) => `${money.format(v)} €`],
    ["trade_summary", "rentabilidad", true, "Mejor rentabilidad trading", "Peor rentabilidad trading", (v) => pct.format(v)],
    ["market_activity_summary", "movimientos_visibles", true, "Más movimiento de mercado", "Menos movimiento de mercado", (v) => `${fmt.format(v)} movimientos`],
    ["signing_points", "puntos_por_fichajes", true, "Más puntos por fichajes", "Menos puntos por fichajes", (v) => `${fmt.format(v)} pts`],
    ["loyalty", "rondas_medias_por_jugador", true, "Equipo más fiel", "Equipo menos fiel", (v) => `${Number(v).toFixed(2)} jornadas`],
    ["concentration", "concentracion_hhi", true, "Puntos más concentrados", "Puntos más repartidos", (v) => Number(v).toFixed(3)],
    ["value_efficiency", "puntos_por_millon", true, "Mejor valor por millón", "Peor valor por millón", (v) => Number(v).toFixed(2)],
  ];
  return definitions.flatMap(([dataset, key, highGood, highTitle, lowTitle, formatter]) => {
    const rows = data[dataset] || [];
    const row = rowForTeam(rows, teamName);
    if (!row || row[key] === undefined || row[key] === null || rows.length === 0) return [];
    const values = rows.map((item) => Number(item[key])).filter((value) => Number.isFinite(value));
    const value = Number(row[key]);
    const max = Math.max(...values);
    const min = Math.min(...values);
    if (max === min) return [];
    if (value === max) return [{ title: highTitle, value: formatter(value), tone: highGood ? "positive" : "negative" }];
    if (value === min) return [{ title: lowTitle, value: formatter(value), tone: highGood ? "negative" : "positive" }];
    return [];
  });
}

function renderTeamProfile(teamName = data.teams[0]?.user_name) {
  const latest = rowForTeam(data.latest_standings, teamName);
  const round = rowForTeam(data.round_counts, teamName);
  const goals = rowForTeam(data.team_goals, teamName);
  const market = rowForTeam(data.market_activity_summary, teamName);
  const trade = rowForTeam(data.trade_summary, teamName);
  const concentration = rowForTeam(data.concentration, teamName);
  const value = rowForTeam(data.value_efficiency, teamName);
  document.getElementById("teamProfileHero").innerHTML = `
    <div class="profile-identity">
      <img src="${teamImage(teamName)}" alt="" loading="lazy" />
      <div>
        <h3>${teamName}</h3>
        <p>${fmt.format(latest.total_points_after_round || 0)} puntos · ${money.format(latest.team_value || 0)} €</p>
      </div>
    </div>
    <p>${teamProfileText(teamName)}</p>
  `;

  const statRows = [
    ["General", latest.league_position ? `#${latest.league_position}` : "-"],
    ["Jornadas ganadas", fmt.format(round.jornadas_ganadas || 0)],
    ["Goles", fmt.format(goals.goles || 0)],
    ["Movimientos", fmt.format(market.movimientos_visibles || 0)],
    ["Beneficio trading", `${money.format(trade.beneficio_bruto || 0)} €`],
    ["Concentración", Number(concentration.concentracion_hhi || 0).toFixed(3)],
    ["Puntos por millón", Number(value.puntos_por_millon || 0).toFixed(2)],
    ["Ranking valor", rankLabel(data.value_efficiency, teamName, "puntos_por_millon", true)],
  ];
  document.getElementById("teamProfileStats").innerHTML = statRows
    .map(([label, value]) => `<div class="stat-card"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");

  const awards = awardRows(teamName);
  document.getElementById("teamAwards").innerHTML = awards.length
    ? awards
        .map(
          (award) =>
            `<div class="award ${award.tone === "negative" ? "negative" : ""}"><strong>${award.title}</strong><span>${award.value}</span></div>`,
        )
        .join("")
    : '<div class="award"><strong>Zona media</strong><span>No es primero ni último en las métricas principales.</span></div>';

  renderTable(
    "teamBestPlayersTable",
    (data.position_best_players || [])
      .filter((row) => teamKey(row.user_name) === teamKey(teamName))
      .sort((a, b) => (a.position_id || 99) - (b.position_id || 99)),
    [
      ["position_name", "Posición"],
      ["player_name", "Jugador"],
      ["player_points", "Puntos", (v) => fmt.format(v)],
      ["goals", "Goles", (v) => fmt.format(v)],
      ["rounds", "Jornadas", (v) => fmt.format(v)],
    ],
  );
}

function setupTeamSelector() {
  const select = document.getElementById("teamSelect");
  if (!select) return;
  select.innerHTML = data.teams
    .map((team) => `<option value="${team.user_name}">${team.user_name}</option>`)
    .join("");
  select.addEventListener("change", () => renderTeamProfile(select.value));
  renderTeamProfile(select.value || data.teams[0]?.user_name);
}

function renderNotes() {
  const coverage = data.meta.coverage;
  document.getElementById("coverageList").innerHTML = [
    `${fmt.format(coverage.lineup_rows)} filas de alineaciones.`,
    `${fmt.format(coverage.lineup_rows_with_player_points)} filas con puntos de jugador.`,
    `${fmt.format(coverage.completed_trade_reconstructions)} trades cerrados reconstruidos.`,
    `${fmt.format(coverage.visible_market_purchases || 0)} compras visibles en el tablón.`,
  ]
    .map((item) => `<li>${item}</li>`)
    .join("");

  document.getElementById("limitsList").innerHTML = data.meta.limitations.map((item) => `<li>${item}</li>`).join("");
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.tab).classList.add("active");
      setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
    });
  });
}

function init() {
  renderScoreboard();
  setupTabs();
  renderPositions();
  renderWinsLosses();
  renderGoalCharts();
  renderPositionCharts();
  renderDiscipline();
  renderMarket();
  renderManagement();
  renderTables();
  setupTeamSelector();
  renderNotes();
}

init();
