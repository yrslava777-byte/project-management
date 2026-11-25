# Практика 4. От требований к плану работ в Битрикс24

**Ярослава Медведева**

В проекте «СЕВЕР» составлен план реализации и будущей проверки резервирования последнего рюкзака по требованиям R1–R5 и сценариям P1–P5 версии 2.

- [Проект «СЕВЕР»](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/)
- [Источник требований и сценариев из практики 3](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/6/)
- [А. Общая задача по резервированию](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/10/)
  - [А1. Создание резерва при оформлении](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/14/)
  - [А2. Срок, отмена и оплата резерва](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/12/)
- [Б. Интерфейс покупателя](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/16/)
- [В. Данные для проверки и чек-лист](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/20/)
- [Г. Сквозная проверка](https://b24-3p9tb1.bitrix24.ru/workgroups/group/2/tasks/task/view/24/)

Для А1 и описания тестовых данных можно начать работу сразу. Для А2 и Б сначала согласуют формат данных и ответов с А1. Сквозной прогон запланирован после готовности А1, А2, Б, В и тестовой среды. На занятии составлен план будущей работы.

## Скриншоты

- [Создание общей задачи А](screenshots/01-parent.png)
- [Создание подзадачи А1](screenshots/02-subtask-a1.png)
- [Связь А с А1](screenshots/03-first-link.png)
- [Создание подзадачи А2](screenshots/04-subtask-a2.png)
- [Обе подзадачи в общей карточке](screenshots/05-two-subtasks.png)
- [Задача Б об интерфейсе](screenshots/06-interface.png)
- [Задача В о тестовых данных](screenshots/07-test-data.png)
- [Настройка чек-листа](screenshots/08-checklist-edit.png)
- [Сохранённый чек-лист из шести пунктов](screenshots/09-checklist-saved.png)
- [Задача Г о сквозной проверке](screenshots/10-end-to-end.png)
- [Сообщение о порядке работ](screenshots/11-work-order.png)

При сверке снимков обнаружено, что в сообщении о порядке работ и в карточке подготовки данных ссылка на источник ведёт на общую задачу А (№ 10). Правильный источник требований и сценариев — задача практики 3 (№ 6), приведённая выше.
