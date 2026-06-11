const data = window.BIWENGER_DASHBOARD_DATA;

const palette = ["#007f79", "#d95f43", "#2d6cdf", "#d6a013", "#248f5a", "#7a4cc2", "#17202a"];

const baseLayout = {
  margin: { l: 64, r: 24, t: 24, b: 68 },
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, system-ui, sans-serif", color: "#17202a" },
  hoverlabel: { bgcolor: "#17202a", font: { color: "white" } },
  xaxis: { gridcolor: "#ece7dc", zerolinecolor: "#ded9ce" },
  yaxis: { gridcolor: "#ece7dc", zerolinecolor: "#ded9ce" },
};

const config = {
  responsive: true,
  displayModeBar: false,
};

const fmt = new Intl.NumberFormat("es-ES");
const pct = new Intl.NumberFormat("es-ES", { style: "percent", maximumFractionDigits: 1 });
const money = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });

function byValue(rows, key, desc = true) {
  return [...rows].sort((a, b) => (desc ? b[key] - a[key] : a[key] - b[key]));
}

function teamColor(name) {
  const idx = data.teams.findIndex((team) => team.user_name === name);
  return palette[(idx < 0 ? 0 : idx) % palette.length];
}

function renderScoreboard() {
  const el = document.getElementById("scoreboard");
  el.innerHTML = data.latest_standings
    .map(
      (row) => `
        <article class="team-tile">
          <span class="rank">${row.league_position}</span>
          <h2>${row.user_name}</h2>
          <p>${fmt.format(row.total_points_after_round)} pts · ${money.format(row.team_value)} €</p>
        </article>
      `,
    )
    .join("");
}

function makeBar(id, rows, xKey, yKey, options = {}) {
  const sorted = options.ascending ? byValue(rows, xKey, false) : byValue(rows, xKey, true);
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
      margin: { l: 132, r: 24, t: 18, b: 44 },
      xaxis: { ...baseLayout.xaxis, title: options.xTitle || "" },
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
      font: { size: 18, color: "#17202a" },
    };
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
      annotations: [titleAnnotation(round)],
    },
  }));

  Plotly.newPlot(
    "positionsChart",
    teams.map((team) => traceForTeam(team, rounds[0])),
    {
      ...baseLayout,
      height: 620,
      margin: { l: 18, r: 150, t: 94, b: 78 },
      annotations: [titleAnnotation(rounds[0])],
      bargap: 0.25,
      yaxis: {
        title: "",
        range: [0.35, data.teams.length + 0.8],
        showticklabels: false,
        showgrid: false,
        zeroline: false,
      },
      xaxis: { title: "Puntos totales", range: [0, maxPoints * 1.12], gridcolor: "#ece7dc" },
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
  Plotly.newPlot(
    "winsLossesChart",
    [
      {
        type: "bar",
        name: "Ganadas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.jornadas_ganadas),
        marker: { color: "#248f5a" },
      },
      {
        type: "bar",
        name: "Perdidas",
        x: rows.map((row) => row.user_name),
        y: rows.map((row) => row.jornadas_perdidas),
        marker: { color: "#d95f43" },
      },
    ],
    {
      ...baseLayout,
      barmode: "group",
      height: 380,
      yaxis: { title: "Jornadas" },
      xaxis: { tickangle: -28 },
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
      xaxis: { tickformat: ".0%", title: "Peso del máximo goleador" },
      yaxis: { autorange: "reversed" },
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
      xaxis: { tickformat: ".0%", title: "Peso del jugador más decisivo" },
      yaxis: { autorange: "reversed" },
    },
    config,
  );
}

function renderDiscipline() {
  Plotly.newPlot(
    "disciplineChart",
    [
      {
        type: "bar",
        x: data.discipline.map((row) => row.user_name),
        y: data.discipline.map((row) => row.palos_index),
        marker: { color: data.discipline.map((row) => teamColor(row.user_name)) },
        customdata: data.discipline.map((row) => [row.amarillas, row.rojas, row.segundas_amarillas]),
        hovertemplate: "%{x}<br>Índice: %{y}<br>Amarillas: %{customdata[0]}<br>Rojas: %{customdata[1]}<extra></extra>",
      },
    ],
    {
      ...baseLayout,
      height: 380,
      xaxis: { tickangle: -28 },
      yaxis: { title: "Índice parcial" },
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

function renderNotes() {
  const coverage = data.meta.coverage;
  document.getElementById("coverageList").innerHTML = [
    `${fmt.format(coverage.lineup_rows)} filas de alineaciones.`,
    `${fmt.format(coverage.lineup_rows_with_player_points)} filas con puntos de jugador.`,
    `${fmt.format(coverage.completed_trade_reconstructions)} trades cerrados reconstruidos.`,
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
  renderDiscipline();
  renderMarket();
  renderManagement();
  renderTables();
  renderNotes();
}

init();
