(() => {
  const app = document.getElementById("app");
  const STORAGE_KEY = "viktorina-rossiya-v2";

  const state = {
    view: "title", // title | board | question | answer | final
    round: 0,
    answered: [new Set(), new Set(), new Set()],
    current: null,
    dismissCompleteOverlay: false,
  };

  function qKey(topicIndex, slot) {
    return `${topicIndex}-${slot}`;
  }

  function roundQuestionIndex(round, slot) {
    return round * 2 + slot;
  }

  function answeredCount(round) {
    return state.answered[round].size;
  }

  function isRoundComplete(round) {
    return answeredCount(round) >= TOPICS.length * 2;
  }

  function saveProgress() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          round: state.round,
          answered: state.answered.map((set) => [...set]),
        })
      );
    } catch (_) {
      /* ignore */
    }
  }

  function loadProgress() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const data = JSON.parse(raw);
      if (!data || !Array.isArray(data.answered)) return false;
      state.round = Math.min(2, Math.max(0, Number(data.round) || 0));
      state.answered = [0, 1, 2].map((i) => new Set(data.answered[i] || []));
      return true;
    } catch (_) {
      return false;
    }
  }

  function clearProgress() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (_) {
      /* ignore */
    }
    state.round = 0;
    state.answered = [new Set(), new Set(), new Set()];
    state.current = null;
    state.dismissCompleteOverlay = false;
  }

  function goToRound(round) {
    state.round = round;
    state.current = null;
    state.dismissCompleteOverlay = false;
    state.view = "board";
    saveProgress();
    render();
  }

  function hasAnyProgress() {
    return state.answered.some((s) => s.size > 0) || state.round > 0;
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function nl2br(s) {
    return escapeHtml(s).replaceAll("\n", "<br />");
  }

  function render() {
    if (state.view === "title") return renderTitle();
    if (state.view === "board") return renderBoard();
    if (state.view === "question") return renderQuestion();
    if (state.view === "answer") return renderAnswer();
    if (state.view === "final") return renderFinal();
  }

  function renderTitle() {
    const saved = hasAnyProgress();
    app.innerHTML = `
      <section class="screen">
        <div class="bg-photo" style="background-image:url('../images/title.jpg')"></div>
        <div class="topbar">
          <div class="brand">Викторина</div>
          <div class="round-pill">3 тура · 5 тем · 30 вопросов</div>
        </div>
        <div class="title-hero">
          <h1>Россия</h1>
          <p>Традиции, история, символы, личности и география.<br />Выбирайте вопрос на табло — команда отвечает — смотрите ответ.</p>
          <div class="title-actions">
            ${
              saved
                ? `<button class="btn btn-primary" id="continueBtn">Продолжить (тур ${ROUND_LABELS[state.round]})</button>`
                : `<button class="btn btn-primary" id="startBtn">Начать I тур</button>`
            }
            <div class="jump-row">
              <span class="jump-label">Сразу к туру:</span>
              <button class="btn btn-secondary btn-sm" data-jump="0">I</button>
              <button class="btn btn-secondary btn-sm" data-jump="1">II</button>
              <button class="btn btn-secondary btn-sm" data-jump="2">III</button>
            </div>
            ${saved ? `<button class="btn btn-ghost" id="resetBtn">Начать заново</button>` : ""}
          </div>
        </div>
      </section>
    `;

    const startBtn = document.getElementById("startBtn");
    if (startBtn) startBtn.onclick = () => goToRound(0);

    const continueBtn = document.getElementById("continueBtn");
    if (continueBtn) continueBtn.onclick = () => goToRound(state.round);

    document.querySelectorAll("[data-jump]").forEach((btn) => {
      btn.onclick = () => goToRound(Number(btn.dataset.jump));
    });

    const resetBtn = document.getElementById("resetBtn");
    if (resetBtn) {
      resetBtn.onclick = () => {
        clearProgress();
        render();
      };
    }
  }

  function bindRoundNav(round) {
    const prev = document.getElementById("prevRoundBtn");
    if (prev) prev.onclick = () => goToRound(round - 1);

    const skipNext = document.getElementById("skipNextBtn");
    if (skipNext) skipNext.onclick = () => goToRound(round + 1);

    const skipFinal = document.getElementById("skipFinalBtn");
    if (skipFinal) {
      skipFinal.onclick = () => {
        state.view = "final";
        saveProgress();
        render();
      };
    }

    const homeBtn = document.getElementById("homeBtn");
    if (homeBtn) {
      homeBtn.onclick = () => {
        state.view = "title";
        state.current = null;
        saveProgress();
        render();
      };
    }

    const fsBtn = document.getElementById("fsBtn");
    if (fsBtn) {
      fsBtn.onclick = () => {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
        else document.exitFullscreen?.();
      };
    }
  }

  function roundNavHtml(round) {
    const prev =
      round > 0
        ? `<button class="btn btn-ghost" id="prevRoundBtn">← Тур ${ROUND_LABELS[round - 1]}</button>`
        : `<span></span>`;
    const next =
      round < 2
        ? `<button class="btn btn-secondary" id="skipNextBtn">К туру ${ROUND_LABELS[round + 1]} →</button>`
        : `<button class="btn btn-secondary" id="skipFinalBtn">К финалу →</button>`;

    return `
      <div class="footer-bar">
        <div class="nav-left">
          ${prev}
          <button class="btn btn-ghost" id="homeBtn">⌂ В начало</button>
        </div>
        <div class="nav-right">
          <button class="btn btn-ghost" id="fsBtn">⛶ Экран</button>
          ${next}
        </div>
      </div>
    `;
  }

  function renderBoard() {
    const round = state.round;
    const done = isRoundComplete(round);
    const left = TOPICS.length * 2 - answeredCount(round);
    const showOverlay = done && !state.dismissCompleteOverlay;

    const rows = TOPICS.map((topic, ti) => {
      const cells = [0, 1]
        .map((slot) => {
          const key = qKey(ti, slot);
          const used = state.answered[round].has(key);
          if (used) {
            return `<button class="q-cell done" disabled aria-label="Вопрос сыгран"></button>`;
          }
          return `<button class="q-cell" data-ti="${ti}" data-slot="${slot}" aria-label="Открыть вопрос">?</button>`;
        })
        .join("");

      return `
        <div class="board-row">
          <div class="topic-cell" style="--topic:${topic.color}">
            <span class="name">${escapeHtml(topic.short)}</span>
          </div>
          ${cells}
        </div>
      `;
    }).join("");

    app.innerHTML = `
      <section class="screen">
        <div class="bg-photo" style="background-image:url('../images/block${(round % 5) + 1}.jpg')"></div>
        <div class="topbar">
          <div class="brand">Викторина «Россия»</div>
          <div class="round-pill">Тур ${ROUND_LABELS[round]}</div>
          <div class="progress">Осталось: ${left}</div>
        </div>
        <div class="main board-wrap">
          <div class="board-title">
            <h2>Табло ${ROUND_LABELS[round]} тура</h2>
            <p>Выберите тему и откройте вопрос</p>
          </div>
          <div class="board">
            <div class="board-head">
              <div>Тема</div>
              <div>Вопрос</div>
              <div>Вопрос</div>
            </div>
            ${rows}
          </div>
          ${roundNavHtml(round)}
        </div>
        ${
          showOverlay
            ? `<div class="round-done">
                <div class="round-done-card">
                  <h3>${round < 2 ? `Тур ${ROUND_LABELS[round]} завершён!` : "Все туры пройдены!"}</h3>
                  <p>${
                    round < 2
                      ? "Все вопросы этого тура сыграны. Можно переходить дальше."
                      : "Отличная игра — можно показать финальный экран."
                  }</p>
                  <button class="btn btn-primary" id="nextRoundBtn">
                    ${round < 2 ? `Перейти к ${ROUND_LABELS[round + 1]} туру` : "К финалу"}
                  </button>
                  <button class="btn btn-ghost" id="stayBtn" style="margin-top:0.7rem">Остаться на табло</button>
                </div>
              </div>`
            : ""
        }
      </section>
    `;

    app.querySelectorAll(".q-cell:not(:disabled)").forEach((btn) => {
      btn.onclick = () => {
        const topicIndex = Number(btn.dataset.ti);
        const slot = Number(btn.dataset.slot);
        state.current = {
          topicIndex,
          slot,
          qIndex: roundQuestionIndex(round, slot),
        };
        state.view = "question";
        saveProgress();
        render();
      };
    });

    bindRoundNav(round);

    const nextBtn = document.getElementById("nextRoundBtn");
    if (nextBtn) {
      nextBtn.onclick = () => {
        if (round < 2) goToRound(round + 1);
        else {
          state.view = "final";
          saveProgress();
          render();
        }
      };
    }

    const stayBtn = document.getElementById("stayBtn");
    if (stayBtn) {
      stayBtn.onclick = () => {
        state.dismissCompleteOverlay = true;
        render();
      };
    }
  }

  function renderQuestion() {
    const { topicIndex, qIndex } = state.current;
    const topic = TOPICS[topicIndex];
    const item = topic.questions[qIndex];

    app.innerHTML = `
      <section class="screen">
        <div class="bg-photo" style="background-image:url('${topic.cover}')"></div>
        <div class="topbar">
          <div class="brand">${escapeHtml(topic.title)}</div>
          <div class="round-pill">Тур ${ROUND_LABELS[state.round]}</div>
          <button class="btn btn-ghost" id="backBoard">← К табло</button>
        </div>
        <div class="main">
          <div class="question-layout">
            <div class="card">
              <div class="card-label">Вопрос</div>
              <h3>${escapeHtml(topic.short)}</h3>
              <p class="question-text">${nl2br(item.q)}</p>
              <div class="card-actions">
                <button class="btn btn-answer" id="showAnswer">Посмотреть ответ</button>
              </div>
            </div>
            <div class="art"><img src="${item.img}" alt="Иллюстрация к вопросу" /></div>
          </div>
        </div>
      </section>
    `;

    document.getElementById("showAnswer").onclick = () => {
      state.view = "answer";
      render();
    };

    document.getElementById("backBoard").onclick = () => {
      state.current = null;
      state.view = "board";
      saveProgress();
      render();
    };
  }

  function renderAnswer() {
    const { topicIndex, slot, qIndex } = state.current;
    const topic = TOPICS[topicIndex];
    const item = topic.questions[qIndex];
    const key = qKey(topicIndex, slot);

    app.innerHTML = `
      <section class="screen answer-screen">
        <div class="bg-photo" style="background-image:url('${item.img}')"></div>
        <div class="topbar">
          <div class="brand">${escapeHtml(topic.short)}</div>
          <div class="round-pill">Тур ${ROUND_LABELS[state.round]} · ответ</div>
        </div>
        <div class="main">
          <div class="answer-card">
            <p class="q-mini">${nl2br(item.q)}</p>
            <div class="label">Правильный ответ</div>
            <p class="answer">${nl2br(item.a)}</p>
            <button class="btn btn-primary" id="backAfterAnswer">Вернуться к табло тура</button>
          </div>
        </div>
      </section>
    `;

    document.getElementById("backAfterAnswer").onclick = () => {
      state.answered[state.round].add(key);
      state.current = null;
      state.dismissCompleteOverlay = false;
      state.view = "board";
      saveProgress();
      render();
    };
  }

  function renderFinal() {
    app.innerHTML = `
      <section class="screen final-screen">
        <div class="bg-photo" style="background-image:url('../images/title.jpg')"></div>
        <div class="topbar">
          <div class="brand">Викторина «Россия»</div>
        </div>
        <div class="title-hero">
          <h1>Молодцы!</h1>
          <p>Все три тура пройдены. Спасибо за игру!</p>
          <div class="title-actions">
            <button class="btn btn-primary" id="restartBtn">Сыграть ещё раз</button>
            <div class="jump-row">
              <span class="jump-label">Вернуться к туру:</span>
              <button class="btn btn-secondary btn-sm" data-jump="0">I</button>
              <button class="btn btn-secondary btn-sm" data-jump="1">II</button>
              <button class="btn btn-secondary btn-sm" data-jump="2">III</button>
            </div>
          </div>
        </div>
      </section>
    `;

    document.getElementById("restartBtn").onclick = () => {
      clearProgress();
      goToRound(0);
    };
    document.querySelectorAll("[data-jump]").forEach((btn) => {
      btn.onclick = () => goToRound(Number(btn.dataset.jump));
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.view === "question") {
      state.current = null;
      state.view = "board";
      saveProgress();
      render();
    }
  });

  loadProgress();
  state.view = "title";
  render();
})();
