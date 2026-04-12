/* ===== TimTag — app.js ===== */

/**
 * Конфетти при правильном ответе
 * Простая реализация без библиотек
 */
function launchConfetti() {
  const colors = ['#6c63ff', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4'];
  const container = document.createElement('div');
  container.style.cssText = `
    position:fixed; top:0; left:0; width:100%; height:100%;
    pointer-events:none; z-index:9999; overflow:hidden;
  `;
  document.body.appendChild(container);

  for (let i = 0; i < 60; i++) {
    const dot = document.createElement('div');
    const size = Math.random() * 10 + 6;
    const color = colors[Math.floor(Math.random() * colors.length)];
    const left = Math.random() * 100;
    const delay = Math.random() * 0.5;
    const duration = Math.random() * 1.5 + 1;
    const rotate = Math.random() * 360;
    const isRect = Math.random() > 0.5;

    dot.style.cssText = `
      position:absolute;
      top:-20px;
      left:${left}%;
      width:${size}px;
      height:${isRect ? size * 0.4 : size}px;
      background:${color};
      border-radius:${isRect ? '2px' : '50%'};
      animation: fall ${duration}s ${delay}s ease-in forwards;
      transform: rotate(${rotate}deg);
      opacity: 0.9;
    `;
    container.appendChild(dot);
  }

  // Добавляем keyframes динамически (один раз)
  if (!document.getElementById('confetti-style')) {
    const style = document.createElement('style');
    style.id = 'confetti-style';
    style.textContent = `
      @keyframes fall {
        0%   { transform: translateY(0) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  setTimeout(() => container.remove(), 3000);
}

/**
 * Звуки (Web Audio API — без файлов)
 */
function playSound(type) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'correct') {
      // Восходящая мелодия
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.setValueAtTime(554, ctx.currentTime + 0.1);
      osc.frequency.setValueAtTime(659, ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.6);
    } else {
      // Низкий звук для ошибки
      osc.frequency.setValueAtTime(300, ctx.currentTime);
      osc.frequency.setValueAtTime(220, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.25, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    }
  } catch (e) {
    // Браузер не поддерживает — молча игнорируем
  }
}

/**
 * Инициализация страницы feedback
 * Вызывается из base.html через data-атрибут
 */
function initFeedback(isCorrect) {
  if (isCorrect) {
    launchConfetti();
    playSound('correct');
  } else {
    playSound('wrong');
  }
}

/**
 * Анимация кнопок-ответов при загрузке задачи
 */
function animateAnswerButtons() {
  const buttons = document.querySelectorAll('.answer-btn');
  buttons.forEach((btn, i) => {
    btn.style.opacity = '0';
    btn.style.transform = 'scale(0.7)';
    setTimeout(() => {
      btn.style.transition = 'opacity 0.2s, transform 0.2s';
      btn.style.opacity = '1';
      btn.style.transform = 'scale(1)';
    }, i * 18);
  });
}

// Запуск при загрузке
document.addEventListener('DOMContentLoaded', () => {
  animateAnswerButtons();
});

// Повторный запуск после HTMX-свапа (когда HTMX заменяет блок)
document.addEventListener('htmx:afterSwap', () => {
  animateAnswerButtons();

  // Проверяем — есть ли на новой странице данные о правильности ответа
  const feedbackEl = document.getElementById('feedback-data');
  if (feedbackEl) {
    const isCorrect = feedbackEl.dataset.correct === 'true';
    initFeedback(isCorrect);
  }
});
