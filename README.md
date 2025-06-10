# journey_english

{% extends "base.html" %}
{% load static %}

{% block content %}

<!-- ─────────── 1. ПРОГРЕСС-БАР ─────────── -->
<div class="progress-bar sticky-progress">
  {% for lq in level_questions %}
    <div class="progress-square {% if lq.id in completed_ids %}done{% endif %}">
      {% if lq.id in completed_ids %}
        ✔
      {% else %}
        {{ forloop.counter }}
      {% endif %}
    </div>
  {% endfor %}
</div>

<!-- ─────────── 2. ОСНОВНОЙ ЭКРАН ─────────── -->
<main class="level_trial">
  <!-- слово на русском -->
  <div class="question-block-trial">
    <p>Переведи это слово на английский:</p>
    <p class="word-rus">{{ question.translation }}</p>
  </div>
  <!-- анимация белки -->
  <div class="squirrel-wrapper">
    <img id="squirrel"
        src="{% static 'img/squirrel_1.svg' %}"
        alt="Белка">
  </div>

  <!-- форма ввода -->
  <div class="trial-form-container">
    <form method="post" id="trial-form" autocomplete="off">
        {% csrf_token %}
        <input type="text"
            name="user_answer"
            class="translation-input"
            id="answer-input"
            placeholder="Введите перевод"
            autofocus>
        <button type="submit" class="next-btn" id="submit-btn">
          Проверить
        </button>
    </form>
  </div>

  <!-- сообщение о попытках -->

{% if result == "wrong" %}
<p class="error">
Неверно. Осталось попыток: {{ attempts_left }}.
</p>
{% endif %}

</main>

<!-- ─────────── 3. JS: анимация и переходы ─────────── -->
<script>
document.addEventListener('DOMContentLoaded', () => {
  const squirrel = document.getElementById('squirrel');
  const form = document.getElementById('trial-form');
  const submitBtn = document.getElementById('submit-btn');
  const answerInput = document.getElementById('answer-input');
  const imgPath = "{% static 'img/' %}";
  const successSeq = ['squirrel_1.svg', 'squirrel_2.svg', 'squirrel_3.svg'];
  const failSeq = ['squirrel_1.svg', 'squirrel_2.svg', 'squirrel_fail.svg'];

  // Функция блокировки/разблокировки формы
  function setFormDisabled(disabled) {
    submitBtn.disabled = disabled;
    answerInput.disabled = disabled;
    if (!disabled) {
      answerInput.focus();
    }
  }

  // Обработчик отправки формы
  form.addEventListener('submit', function(e) {
    // Блокируем форму только если ответ правильный или закончились попытки
    if ("{{ result }}" !== "wrong") {
      setFormDisabled(true);
    }
  });

  /** Покадрово проигрываем массив SVG, затем вызываем callback */
  function play(seq, cb) {
    let i = 0;
    const next = () => {
      if (i < seq.length) {
        squirrel.src = imgPath + seq[i++];
        setTimeout(next, 350);
      } else if (cb) cb();
    };
    next();
  }

  {% if result == "success" %}
    setFormDisabled(true);
    play(successSeq, () => window.location = "{{ next_url }}");
  {% elif result == "fail" %}
    setFormDisabled(true);
    play(failSeq, () => window.location = "{{ fail_url }}");
  {% endif %}
});
</script>

{% endblock %}
