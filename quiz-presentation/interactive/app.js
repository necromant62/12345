(() => {
  const app = document.getElementById("app");

  const state = {
    view: "title", // title | board | question | answer | final
    round: 0, // 0..2
    answered: [new Set(), new Set(), new Set()], // keys "topicIndex-slot" slot 0|1
    current: null, // { topicIndex, slot, qIndex }
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
    app.innerHTML = `
      <section class="screen">
        <div class="bg-photo" style="background-image:url('../images/title.jpg')"></div>
        <div class="topbar">
          <div class="brand">Викторина</div>
          <div class="round-pill">3 тура · 5 тем · 30 вопросов</div>
        </div>
        <div class="title-hero">
          <h1>Россия</h1>
          <p>Традиции, история, символы, личности и география.<br />Выбирайте вопрос на табло тура — команда отвечает — смотрите ответ.</p>
          <button class="btn btn-primary" id="startBtn">Начать I тур</button>
        </div>
      </section>
    `;
    document.getElementById("startBtn").onclick = () => {
      state.round = 0;
      state.view = "board";
      render();
    };
  }

  function renderBoard() {
    const round = state.round;
    const done = isRoundComplete(round);
    const left = TOPICS.length * 2 - answeredCount(round);

    const rows = TOPICS.map((topic, ti) => {
      const cells = [0, 1]
        .map((slot) => {
          const key = qKey(ti, slot);
          const used = state.answered[round].has(key);
          if (used) {
            return `<button class="q-cell done" disabled aria-label="Вопрос сыгран"></button>`;
          }
          return `<button class="q-cell" data-ti="${ti}" data-slot="${slot}">${slot + 1}</button>`;
        })
        .join("");

      return `
        <div class="board-row">
          <div class="topic-cell" style="--topic:${topic.color}">
            <span class="dot"></span>
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
          <div class="progress">Осталось вопросов: ${left}</div>
        </div>
        <div class="main board-wrap">
          <div class="board-title">
            <h2>Табло ${ROUND_LABELS[round]} тура</h2>
            <p>Выберите вопрос: тема → номер 1 или 2</p>
          </div>
          <div class="board">
            <div class="board-head">
              <div>Тема</div>
              <div>Вопрос 1</div>
              <div>Вопрос 2</div>
            </div>
            ${rows}
          </div>
          <div class="footer-bar">
            <div class="hint">Сыгранные вопросы исчезают с табло</div>
            ${
              done
                ? ""
                : `<button class="btn btn-ghost" id="fsBtn" title="На весь экран">⛶ На весь экран</button>`
            }
          </div>
        </div>
        ${
          done
            ? `<div class="round-done">
                <div class="round-done-card">
                  <h3>${round < 2 ? `Тур ${ROUND_LABELS[round]} завершён!` : "Все туры пройдены!"}</h3>
                  <p>${
                    round < 2
                      ? "Все 10 вопросов этого тура сыграны. Можно переходить дальше."
                      : "Отличная игра — можно показать финальный экран."
                  }</p>
                  <button class="btn btn-primary" id="nextRoundBtn">
                    ${round < 2 ? `Перейти к ${ROUND_LABELS[round + 1]} туру` : "К финалу"}
                  </button>
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
        const qIndex = roundQuestionIndex(round, slot);
        state.current = { topicIndex, slot, qIndex };
        state.view = "question";
        render();
      };
    });

    const fsBtn = document.getElementById("fsBtn");
    if (fsBtn) {
      fsBtn.onclick = () => {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
        else document.exitFullscreen?.();
      };
    }

    const nextBtn = document.getElementById("nextRoundBtn");
    if (nextBtn) {
      nextBtn.onclick = () => {
        if (round < 2) {
          state.round = round + 1;
          state.view = "board";
        } else {
          state.view = "final";
        }
        render();
      };
    }
  }

  function renderQuestion() {
    const { topicIndex, slot, qIndex } = state.current;
    const topic = TOPICS[topicIndex];
    const item = topic.questions[qIndex];

    app.innerHTML = `
      <section class="screen">
        <div class="bg-photo" style="background-image:url('${topic.cover}')"></div>
        <div class="topbar">
          <div class="brand">${escapeHtml(topic.title)}</div>
          <div class="round-pill">Тур ${ROUND_LABELS[state.round]} · вопрос ${slot + 1}</div>
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
      // Returning without answering does NOT consume the question
      state.current = null;
      state.view = "board";
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
      state.view = "board";
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
          <button class="btn btn-primary" id="restartBtn">Сыграть ещё раз</button>
        </div>
      </section>
    `;
    document.getElementById("restartBtn").onclick = () => {
      state.view = "title";
      state.round = 0;
      state.answered = [new Set(), new Set(), new Set()];
      state.current = null;
      render();
    };
  }

  // Keyboard helpers for presenter
  document.addEventListener("keydown", (e) => {
    if (e.key === "F11") return;
    if (e.key === "Escape" && state.view === "question") {
      state.current = null;
      state.view = "board";
      render();
    }
  });

  render();
})();
