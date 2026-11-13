/**
 * Moliya (Kalkulator) — Frontend Application Engine
 * Asynchronous pure vanilla JS with live REST API integration
 */

const API_BASE = '/api/v1';

// ==========================================
// IKONKALAR — Phosphor Icons (phosphoricons.com, MIT litsenziya; @phosphor-icons/core 2.1.1 dan olingan)
// Regular vazn, 256x256 koordinatada to'ldirilgan shakllar. Kichik nishonlardagi Kirim/Chiqim strelkalari — Bold:
// ~11px da regular juda ingichka. Yangi ikonka kerak bo'lsa phosphoricons.com dan shu vaznda oling.
// Litsenziya matni (MIT, Copyright (c) 2023 Phosphor Icons): static/js/THIRD_PARTY_LICENSES.txt
// ==========================================

const ICONS = {
  settings:       '<path d="M128,80a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Zm88-29.84q.06-2.16,0-4.32l14.92-18.64a8,8,0,0,0,1.48-7.06,107.21,107.21,0,0,0-10.88-26.25,8,8,0,0,0-6-3.93l-23.72-2.64q-1.48-1.56-3-3L186,40.54a8,8,0,0,0-3.94-6,107.71,107.71,0,0,0-26.25-10.87,8,8,0,0,0-7.06,1.49L130.16,40Q128,40,125.84,40L107.2,25.11a8,8,0,0,0-7.06-1.48A107.6,107.6,0,0,0,73.89,34.51a8,8,0,0,0-3.93,6L67.32,64.27q-1.56,1.49-3,3L40.54,70a8,8,0,0,0-6,3.94,107.71,107.71,0,0,0-10.87,26.25,8,8,0,0,0,1.49,7.06L40,125.84Q40,128,40,130.16L25.11,148.8a8,8,0,0,0-1.48,7.06,107.21,107.21,0,0,0,10.88,26.25,8,8,0,0,0,6,3.93l23.72,2.64q1.49,1.56,3,3L70,215.46a8,8,0,0,0,3.94,6,107.71,107.71,0,0,0,26.25,10.87,8,8,0,0,0,7.06-1.49L125.84,216q2.16.06,4.32,0l18.64,14.92a8,8,0,0,0,7.06,1.48,107.21,107.21,0,0,0,26.25-10.88,8,8,0,0,0,3.93-6l2.64-23.72q1.56-1.48,3-3L215.46,186a8,8,0,0,0,6-3.94,107.71,107.71,0,0,0,10.87-26.25,8,8,0,0,0-1.49-7.06Zm-16.1-6.5a73.93,73.93,0,0,1,0,8.68,8,8,0,0,0,1.74,5.48l14.19,17.73a91.57,91.57,0,0,1-6.23,15L187,173.11a8,8,0,0,0-5.1,2.64,74.11,74.11,0,0,1-6.14,6.14,8,8,0,0,0-2.64,5.1l-2.51,22.58a91.32,91.32,0,0,1-15,6.23l-17.74-14.19a8,8,0,0,0-5-1.75h-.48a73.93,73.93,0,0,1-8.68,0,8,8,0,0,0-5.48,1.74L100.45,215.8a91.57,91.57,0,0,1-15-6.23L82.89,187a8,8,0,0,0-2.64-5.1,74.11,74.11,0,0,1-6.14-6.14,8,8,0,0,0-5.1-2.64L46.43,170.6a91.32,91.32,0,0,1-6.23-15l14.19-17.74a8,8,0,0,0,1.74-5.48,73.93,73.93,0,0,1,0-8.68,8,8,0,0,0-1.74-5.48L40.2,100.45a91.57,91.57,0,0,1,6.23-15L69,82.89a8,8,0,0,0,5.1-2.64,74.11,74.11,0,0,1,6.14-6.14A8,8,0,0,0,82.89,69L85.4,46.43a91.32,91.32,0,0,1,15-6.23l17.74,14.19a8,8,0,0,0,5.48,1.74,73.93,73.93,0,0,1,8.68,0,8,8,0,0,0,5.48-1.74L155.55,40.2a91.57,91.57,0,0,1,15,6.23L173.11,69a8,8,0,0,0,2.64,5.1,74.11,74.11,0,0,1,6.14,6.14,8,8,0,0,0,5.1,2.64l22.58,2.51a91.32,91.32,0,0,1,6.23,15l-14.19,17.74A8,8,0,0,0,199.87,123.66Z"/>',
  logout:         '<path d="M120,216a8,8,0,0,1-8,8H48a8,8,0,0,1-8-8V40a8,8,0,0,1,8-8h64a8,8,0,0,1,0,16H56V208h56A8,8,0,0,1,120,216Zm109.66-93.66-40-40a8,8,0,0,0-11.32,11.32L204.69,120H112a8,8,0,0,0,0,16h92.69l-26.35,26.34a8,8,0,0,0,11.32,11.32l40-40A8,8,0,0,0,229.66,122.34Z"/>',
  chevronLeft:    '<path d="M165.66,202.34a8,8,0,0,1-11.32,11.32l-80-80a8,8,0,0,1,0-11.32l80-80a8,8,0,0,1,11.32,11.32L91.31,128Z"/>',
  chevronRight:   '<path d="M181.66,133.66l-80,80a8,8,0,0,1-11.32-11.32L164.69,128,90.34,53.66a8,8,0,0,1,11.32-11.32l80,80A8,8,0,0,1,181.66,133.66Z"/>',
  chevronDown:    '<path d="M213.66,101.66l-80,80a8,8,0,0,1-11.32,0l-80-80A8,8,0,0,1,53.66,90.34L128,164.69l74.34-74.35a8,8,0,0,1,11.32,11.32Z"/>',
  receipt:        '<path d="M72,104a8,8,0,0,1,8-8h96a8,8,0,0,1,0,16H80A8,8,0,0,1,72,104Zm8,40h96a8,8,0,0,0,0-16H80a8,8,0,0,0,0,16ZM232,56V208a8,8,0,0,1-11.58,7.15L192,200.94l-28.42,14.21a8,8,0,0,1-7.16,0L128,200.94,99.58,215.15a8,8,0,0,1-7.16,0L64,200.94,35.58,215.15A8,8,0,0,1,24,208V56A16,16,0,0,1,40,40H216A16,16,0,0,1,232,56Zm-16,0H40V195.06l20.42-10.22a8,8,0,0,1,7.16,0L96,199.06l28.42-14.22a8,8,0,0,1,7.16,0L160,199.06l28.42-14.22a8,8,0,0,1,7.16,0L216,195.06Z"/>',
  chart:          '<path d="M224,200h-8V40a8,8,0,0,0-8-8H152a8,8,0,0,0-8,8V80H96a8,8,0,0,0-8,8v40H48a8,8,0,0,0-8,8v64H32a8,8,0,0,0,0,16H224a8,8,0,0,0,0-16ZM160,48h40V200H160ZM104,96h40V200H104ZM56,144H88v56H56Z"/>',
  wallet:         '<path d="M216,64H56a8,8,0,0,1,0-16H192a8,8,0,0,0,0-16H56A24,24,0,0,0,32,56V184a24,24,0,0,0,24,24H216a16,16,0,0,0,16-16V80A16,16,0,0,0,216,64Zm0,128H56a8,8,0,0,1-8-8V78.63A23.84,23.84,0,0,0,56,80H216Zm-48-60a12,12,0,1,1,12,12A12,12,0,0,1,168,132Z"/>',
  ledger:         '<path d="M184,112a8,8,0,0,1-8,8H112a8,8,0,0,1,0-16h64A8,8,0,0,1,184,112Zm-8,24H112a8,8,0,0,0,0,16h64a8,8,0,0,0,0-16Zm48-88V208a16,16,0,0,1-16,16H48a16,16,0,0,1-16-16V48A16,16,0,0,1,48,32H208A16,16,0,0,1,224,48ZM48,208H72V48H48Zm160,0V48H88V208H208Z"/>',
  members:        '<path d="M117.25,157.92a60,60,0,1,0-66.5,0A95.83,95.83,0,0,0,3.53,195.63a8,8,0,1,0,13.4,8.74,80,80,0,0,1,134.14,0,8,8,0,0,0,13.4-8.74A95.83,95.83,0,0,0,117.25,157.92ZM40,108a44,44,0,1,1,44,44A44.05,44.05,0,0,1,40,108Zm210.14,98.7a8,8,0,0,1-11.07-2.33A79.83,79.83,0,0,0,172,168a8,8,0,0,1,0-16,44,44,0,1,0-16.34-84.87,8,8,0,1,1-5.94-14.85,60,60,0,0,1,55.53,105.64,95.83,95.83,0,0,1,47.22,37.71A8,8,0,0,1,250.14,206.7Z"/>',
  expense:        '<path d="M128,88a40,40,0,1,0,40,40A40,40,0,0,0,128,88Zm0,64a24,24,0,1,1,24-24A24,24,0,0,1,128,152ZM240,56H16a8,8,0,0,0-8,8V192a8,8,0,0,0,8,8H240a8,8,0,0,0,8-8V64A8,8,0,0,0,240,56ZM193.65,184H62.35A56.78,56.78,0,0,0,24,145.65v-35.3A56.78,56.78,0,0,0,62.35,72h131.3A56.78,56.78,0,0,0,232,110.35v35.3A56.78,56.78,0,0,0,193.65,184ZM232,93.37A40.81,40.81,0,0,1,210.63,72H232ZM45.37,72A40.81,40.81,0,0,1,24,93.37V72ZM24,162.63A40.81,40.81,0,0,1,45.37,184H24ZM210.63,184A40.81,40.81,0,0,1,232,162.63V184Z"/>',
  income:         '<path d="M240,56v64a8,8,0,0,1-16,0V75.31l-82.34,82.35a8,8,0,0,1-11.32,0L96,123.31,29.66,189.66a8,8,0,0,1-11.32-11.32l72-72a8,8,0,0,1,11.32,0L136,140.69,212.69,64H168a8,8,0,0,1,0-16h64A8,8,0,0,1,240,56Z"/>',
  transfer:       '<path d="M213.66,181.66l-32,32a8,8,0,0,1-11.32-11.32L188.69,184H48a8,8,0,0,1,0-16H188.69l-18.35-18.34a8,8,0,0,1,11.32-11.32l32,32A8,8,0,0,1,213.66,181.66Zm-139.32-64a8,8,0,0,0,11.32-11.32L67.31,88H208a8,8,0,0,0,0-16H67.31L85.66,53.66A8,8,0,0,0,74.34,42.34l-32,32a8,8,0,0,0,0,11.32Z"/>',
  card:           '<path d="M224,48H32A16,16,0,0,0,16,64V192a16,16,0,0,0,16,16H224a16,16,0,0,0,16-16V64A16,16,0,0,0,224,48Zm0,16V88H32V64Zm0,128H32V104H224v88Zm-16-24a8,8,0,0,1-8,8H168a8,8,0,0,1,0-16h32A8,8,0,0,1,208,168Zm-64,0a8,8,0,0,1-8,8H120a8,8,0,0,1,0-16h16A8,8,0,0,1,144,168Z"/>',
  trash:          '<path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM96,40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8v8H96Zm96,168H64V64H192ZM112,104v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Z"/>',
  edit:           '<path d="M227.31,73.37,182.63,28.68a16,16,0,0,0-22.63,0L36.69,152A15.86,15.86,0,0,0,32,163.31V208a16,16,0,0,0,16,16H92.69A15.86,15.86,0,0,0,104,219.31L227.31,96a16,16,0,0,0,0-22.63ZM92.69,208H48V163.31l88-88L180.69,120ZM192,108.68,147.31,64l24-24L216,84.68Z"/>',
  check:          '<path d="M173.66,98.34a8,8,0,0,1,0,11.32l-56,56a8,8,0,0,1-11.32,0l-24-24a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35A8,8,0,0,1,173.66,98.34ZM232,128A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"/>',
  warning:        '<path d="M236.8,188.09,149.35,36.22h0a24.76,24.76,0,0,0-42.7,0L19.2,188.09a23.51,23.51,0,0,0,0,23.72A24.35,24.35,0,0,0,40.55,224h174.9a24.35,24.35,0,0,0,21.33-12.19A23.51,23.51,0,0,0,236.8,188.09ZM222.93,203.8a8.5,8.5,0,0,1-7.48,4.2H40.55a8.5,8.5,0,0,1-7.48-4.2,7.59,7.59,0,0,1,0-7.72L120.52,44.21a8.75,8.75,0,0,1,15,0l87.45,151.87A7.59,7.59,0,0,1,222.93,203.8ZM120,144V104a8,8,0,0,1,16,0v40a8,8,0,0,1-16,0Zm20,36a12,12,0,1,1-12-12A12,12,0,0,1,140,180Z"/>',
  person:         '<path d="M230.92,212c-15.23-26.33-38.7-45.21-66.09-54.16a72,72,0,1,0-73.66,0C63.78,166.78,40.31,185.66,25.08,212a8,8,0,1,0,13.85,8c18.84-32.56,52.14-52,89.07-52s70.23,19.44,89.07,52a8,8,0,1,0,13.85-8ZM72,96a56,56,0,1,1,56,56A56.06,56.06,0,0,1,72,96Z"/>',
  tag:            '<path d="M243.31,136,144,36.69A15.86,15.86,0,0,0,132.69,32H40a8,8,0,0,0-8,8v92.69A15.86,15.86,0,0,0,36.69,144L136,243.31a16,16,0,0,0,22.63,0l84.68-84.68a16,16,0,0,0,0-22.63Zm-96,96L48,132.69V48h84.69L232,147.31ZM96,84A12,12,0,1,1,84,72,12,12,0,0,1,96,84Z"/>',
  pin:            '<path d="M128,64a40,40,0,1,0,40,40A40,40,0,0,0,128,64Zm0,64a24,24,0,1,1,24-24A24,24,0,0,1,128,128Zm0-112a88.1,88.1,0,0,0-88,88c0,31.4,14.51,64.68,42,96.25a254.19,254.19,0,0,0,41.45,38.3,8,8,0,0,0,9.18,0A254.19,254.19,0,0,0,174,200.25c27.45-31.57,42-64.85,42-96.25A88.1,88.1,0,0,0,128,16Zm0,206c-16.53-13-72-60.75-72-118a72,72,0,0,1,144,0C200,161.23,144.53,209,128,222Z"/>',
  note:           '<path d="M88,96a8,8,0,0,1,8-8h64a8,8,0,0,1,0,16H96A8,8,0,0,1,88,96Zm8,40h64a8,8,0,0,0,0-16H96a8,8,0,0,0,0,16Zm32,16H96a8,8,0,0,0,0,16h32a8,8,0,0,0,0-16ZM224,48V156.69A15.86,15.86,0,0,1,219.31,168L168,219.31A15.86,15.86,0,0,1,156.69,224H48a16,16,0,0,1-16-16V48A16,16,0,0,1,48,32H208A16,16,0,0,1,224,48ZM48,208H152V160a8,8,0,0,1,8-8h48V48H48Zm120-40v28.7L196.69,168Z"/>',
  calendar:       '<path d="M208,32H184V24a8,8,0,0,0-16,0v8H88V24a8,8,0,0,0-16,0v8H48A16,16,0,0,0,32,48V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V48A16,16,0,0,0,208,32ZM72,48v8a8,8,0,0,0,16,0V48h80v8a8,8,0,0,0,16,0V48h24V80H48V48ZM208,208H48V96H208V208Z"/>',
  folder:         '<path d="M216,72H131.31L104,44.69A15.86,15.86,0,0,0,92.69,40H40A16,16,0,0,0,24,56V200.62A15.4,15.4,0,0,0,39.38,216H216.89A15.13,15.13,0,0,0,232,200.89V88A16,16,0,0,0,216,72ZM40,56H92.69l16,16H40ZM216,200H40V88H216Z"/>',
  up:             '<path d="M205.66,117.66a8,8,0,0,1-11.32,0L136,59.31V216a8,8,0,0,1-16,0V59.31L61.66,117.66a8,8,0,0,1-11.32-11.32l72-72a8,8,0,0,1,11.32,0l72,72A8,8,0,0,1,205.66,117.66Z"/>',
  down:           '<path d="M205.66,149.66l-72,72a8,8,0,0,1-11.32,0l-72-72a8,8,0,0,1,11.32-11.32L120,196.69V40a8,8,0,0,1,16,0V196.69l58.34-58.35a8,8,0,0,1,11.32,11.32Z"/>',
  clock:          '<path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm64-88a8,8,0,0,1-8,8H128a8,8,0,0,1-8-8V72a8,8,0,0,1,16,0v48h48A8,8,0,0,1,192,128Z"/>',
  plus:           '<path d="M224,128a8,8,0,0,1-8,8H136v80a8,8,0,0,1-16,0V136H40a8,8,0,0,1,0-16h80V40a8,8,0,0,1,16,0v80h80A8,8,0,0,1,224,128Z"/>',
  incomeArrow:    '<path d="M204,64V168a12,12,0,0,1-24,0V93L72.49,200.49a12,12,0,0,1-17-17L163,76H88a12,12,0,0,1,0-24H192A12,12,0,0,1,204,64Z"/>',
  expenseArrow:   '<path d="M204,88V192a12,12,0,0,1-12,12H88a12,12,0,0,1,0-24h75L55.51,72.48a12,12,0,0,1,17-17L180,163V88a12,12,0,0,1,24,0Z"/>',
  arrowUpRight:   '<path d="M200,64V168a8,8,0,0,1-16,0V83.31L69.66,197.66a8,8,0,0,1-11.32-11.32L172.69,72H88a8,8,0,0,1,0-16H192A8,8,0,0,1,200,64Z"/>',
  arrowDownRight: '<path d="M200,88V192a8,8,0,0,1-8,8H88a8,8,0,0,1,0-16h84.69L58.34,69.66A8,8,0,0,1,69.66,58.34L184,172.69V88a8,8,0,0,1,16,0Z"/>',
  desktop:        '<path d="M208,40H48A24,24,0,0,0,24,64V176a24,24,0,0,0,24,24h72v16H96a8,8,0,0,0,0,16h64a8,8,0,0,0,0-16H136V200h72a24,24,0,0,0,24-24V64A24,24,0,0,0,208,40ZM48,56H208a8,8,0,0,1,8,8v80H40V64A8,8,0,0,1,48,56ZM208,184H48a8,8,0,0,1-8-8V160H216v16A8,8,0,0,1,208,184Z"/>',
  mobile:         '<path d="M176,16H80A24,24,0,0,0,56,40V216a24,24,0,0,0,24,24h96a24,24,0,0,0,24-24V40A24,24,0,0,0,176,16ZM72,64H184V192H72Zm8-32h96a8,8,0,0,1,8,8v8H72V40A8,8,0,0,1,80,32Zm96,192H80a8,8,0,0,1-8-8v-8H184v8A8,8,0,0,1,176,224Z"/>',
  tablet:         '<path d="M192,24H64A24,24,0,0,0,40,48V208a24,24,0,0,0,24,24H192a24,24,0,0,0,24-24V48A24,24,0,0,0,192,24ZM56,72H200V184H56Zm8-32H192a8,8,0,0,1,8,8v8H56V48A8,8,0,0,1,64,40ZM192,216H64a8,8,0,0,1-8-8v-8H200v8A8,8,0,0,1,192,216Z"/>',
  repeat:         '<path d="M24,128A72.08,72.08,0,0,1,96,56H204.69L194.34,45.66a8,8,0,0,1,11.32-11.32l24,24a8,8,0,0,1,0,11.32l-24,24a8,8,0,0,1-11.32-11.32L204.69,72H96a56.06,56.06,0,0,0-56,56,8,8,0,0,1-16,0Zm200-8a8,8,0,0,0-8,8,56.06,56.06,0,0,1-56,56H51.31l10.35-10.34a8,8,0,0,0-11.32-11.32l-24,24a8,8,0,0,0,0,11.32l24,24a8,8,0,0,0,11.32-11.32L51.31,200H160a72.08,72.08,0,0,0,72-72A8,8,0,0,0,224,120Z"/>',
  target:         '<path d="M221.87,83.16A104.1,104.1,0,1,1,195.67,49l22.67-22.68a8,8,0,0,1,11.32,11.32l-96,96a8,8,0,0,1-11.32-11.32l27.72-27.72a40,40,0,1,0,17.87,31.09,8,8,0,1,1,16-.9,56,56,0,1,1-22.38-41.65L184.3,60.39a87.88,87.88,0,1,0,23.13,29.67,8,8,0,0,1,14.44-6.9Z"/>',
  shield:         '<path d="M208,40H48A16,16,0,0,0,32,56v56c0,52.72,25.52,84.67,46.93,102.19,23.06,18.86,46,25.26,47,25.53a8,8,0,0,0,4.2,0c1-.27,23.91-6.67,47-25.53C198.48,196.67,224,164.72,224,112V56A16,16,0,0,0,208,40Zm0,72c0,37.07-13.66,67.16-40.6,89.42A129.3,129.3,0,0,1,128,223.62a128.25,128.25,0,0,1-38.92-21.81C61.82,179.51,48,149.3,48,112l0-56,160,0ZM82.34,141.66a8,8,0,0,1,11.32-11.32L112,148.69l50.34-50.35a8,8,0,0,1,11.32,11.32l-56,56a8,8,0,0,1-11.32,0Z"/>',
  lock:           '<path d="M208,80H176V56a48,48,0,0,0-96,0V80H48A16,16,0,0,0,32,96V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V96A16,16,0,0,0,208,80ZM96,56a32,32,0,0,1,64,0V80H96ZM208,208H48V96H208V208Zm-68-56a12,12,0,1,1-12-12A12,12,0,0,1,140,152Z"/>',
  palette:        '<path d="M200.77,53.89A103.27,103.27,0,0,0,128,24h-1.07A104,104,0,0,0,24,128c0,43,26.58,79.06,69.36,94.17A32,32,0,0,0,136,192a16,16,0,0,1,16-16h46.21a31.81,31.81,0,0,0,31.2-24.88,104.43,104.43,0,0,0,2.59-24A103.28,103.28,0,0,0,200.77,53.89Zm13,93.71A15.89,15.89,0,0,1,198.21,160H152a32,32,0,0,0-32,32,16,16,0,0,1-21.31,15.07C62.49,194.3,40,164,40,128a88,88,0,0,1,87.09-88h.9a88.35,88.35,0,0,1,88,87.25A88.86,88.86,0,0,1,213.81,147.6ZM140,76a12,12,0,1,1-12-12A12,12,0,0,1,140,76ZM96,100A12,12,0,1,1,84,88,12,12,0,0,1,96,100Zm0,56a12,12,0,1,1-12-12A12,12,0,0,1,96,156Zm88-56a12,12,0,1,1-12-12A12,12,0,0,1,184,100Z"/>',
  globe:          '<path d="M128,24h0A104,104,0,1,0,232,128,104.12,104.12,0,0,0,128,24Zm88,104a87.61,87.61,0,0,1-3.33,24H174.16a157.44,157.44,0,0,0,0-48h38.51A87.61,87.61,0,0,1,216,128ZM102,168H154a115.11,115.11,0,0,1-26,45A115.27,115.27,0,0,1,102,168Zm-3.9-16a140.84,140.84,0,0,1,0-48h59.88a140.84,140.84,0,0,1,0,48ZM40,128a87.61,87.61,0,0,1,3.33-24H81.84a157.44,157.44,0,0,0,0,48H43.33A87.61,87.61,0,0,1,40,128ZM154,88H102a115.11,115.11,0,0,1,26-45A115.27,115.27,0,0,1,154,88Zm52.33,0H170.71a135.28,135.28,0,0,0-22.3-45.6A88.29,88.29,0,0,1,206.37,88ZM107.59,42.4A135.28,135.28,0,0,0,85.29,88H49.63A88.29,88.29,0,0,1,107.59,42.4ZM49.63,168H85.29a135.28,135.28,0,0,0,22.3,45.6A88.29,88.29,0,0,1,49.63,168Zm98.78,45.6a135.28,135.28,0,0,0,22.3-45.6h35.66A88.29,88.29,0,0,1,148.41,213.6Z"/>',
  help:           '<path d="M140,180a12,12,0,1,1-12-12A12,12,0,0,1,140,180ZM128,72c-22.06,0-40,16.15-40,36v4a8,8,0,0,0,16,0v-4c0-11,10.77-20,24-20s24,9,24,20-10.77,20-24,20a8,8,0,0,0-8,8v8a8,8,0,0,0,16,0v-.72c18.24-3.35,32-17.9,32-35.28C168,88.15,150.06,72,128,72Zm104,56A104,104,0,1,1,128,24,104.11,104.11,0,0,1,232,128Zm-16,0a88,88,0,1,0-88,88A88.1,88.1,0,0,0,216,128Z"/>',
  sparkle:        '<path d="M197.58,129.06,146,110l-19-51.62a15.92,15.92,0,0,0-29.88,0L78,110l-51.62,19a15.92,15.92,0,0,0,0,29.88L78,178l19,51.62a15.92,15.92,0,0,0,29.88,0L146,178l51.62-19a15.92,15.92,0,0,0,0-29.88ZM137,164.22a8,8,0,0,0-4.74,4.74L112,223.85,91.78,169A8,8,0,0,0,87,164.22L32.15,144,87,123.78A8,8,0,0,0,91.78,119L112,64.15,132.22,119a8,8,0,0,0,4.74,4.74L191.85,144ZM144,40a8,8,0,0,1,8-8h16V16a8,8,0,0,1,16,0V32h16a8,8,0,0,1,0,16H184V64a8,8,0,0,1-16,0V48H152A8,8,0,0,1,144,40ZM248,88a8,8,0,0,1-8,8h-8v8a8,8,0,0,1-16,0V96h-8a8,8,0,0,1,0-16h8V72a8,8,0,0,1,16,0v8h8A8,8,0,0,1,248,88Z"/>',
  chat:           '<path d="M140,128a12,12,0,1,1-12-12A12,12,0,0,1,140,128ZM84,116a12,12,0,1,0,12,12A12,12,0,0,0,84,116Zm88,0a12,12,0,1,0,12,12A12,12,0,0,0,172,116Zm60,12A104,104,0,0,1,79.12,219.82L45.07,231.17a16,16,0,0,1-20.24-20.24l11.35-34.05A104,104,0,1,1,232,128Zm-16,0A88,88,0,1,0,51.81,172.06a8,8,0,0,1,.66,6.54L40,216,77.4,203.53a7.85,7.85,0,0,1,2.53-.42,8,8,0,0,1,4,1.08A88,88,0,0,0,216,128Z"/>',
  info:           '<path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm16-40a8,8,0,0,1-8,8,16,16,0,0,1-16-16V128a8,8,0,0,1,0-16,16,16,0,0,1,16,16v40A8,8,0,0,1,144,176ZM112,84a12,12,0,1,1,12,12A12,12,0,0,1,112,84Z"/>',
  send:           '<path d="M231.87,114l-168-95.89A16,16,0,0,0,40.92,37.34L71.55,128,40.92,218.67A16,16,0,0,0,56,240a16.15,16.15,0,0,0,7.93-2.1l167.92-96.05a16,16,0,0,0,.05-27.89ZM56,224a.56.56,0,0,0,0-.12L85.74,136H144a8,8,0,0,0,0-16H85.74L56.06,32.16A.46.46,0,0,0,56,32l168,95.83Z"/>',
  exchange:       '<path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm40-68a28,28,0,0,1-28,28h-4v8a8,8,0,0,1-16,0v-8H104a8,8,0,0,1,0-16h36a12,12,0,0,0,0-24H116a28,28,0,0,1,0-56h4V72a8,8,0,0,1,16,0v8h16a8,8,0,0,1,0,16H116a12,12,0,0,0,0,24h24A28,28,0,0,1,168,148Z"/>',
  sun:            '<path d="M120,40V16a8,8,0,0,1,16,0V40a8,8,0,0,1-16,0Zm72,88a64,64,0,1,1-64-64A64.07,64.07,0,0,1,192,128Zm-16,0a48,48,0,1,0-48,48A48.05,48.05,0,0,0,176,128ZM58.34,69.66A8,8,0,0,0,69.66,58.34l-16-16A8,8,0,0,0,42.34,53.66Zm0,116.68-16,16a8,8,0,0,0,11.32,11.32l16-16a8,8,0,0,0-11.32-11.32ZM192,72a8,8,0,0,0,5.66-2.34l16-16a8,8,0,0,0-11.32-11.32l-16,16A8,8,0,0,0,192,72Zm5.66,114.34a8,8,0,0,0-11.32,11.32l16,16a8,8,0,0,0,11.32-11.32ZM48,128a8,8,0,0,0-8-8H16a8,8,0,0,0,0,16H40A8,8,0,0,0,48,128Zm80,80a8,8,0,0,0-8,8v24a8,8,0,0,0,16,0V216A8,8,0,0,0,128,208Zm112-88H216a8,8,0,0,0,0,16h24a8,8,0,0,0,0-16Z"/>',
  moon:           '<path d="M233.54,142.23a8,8,0,0,0-8-2,88.08,88.08,0,0,1-109.8-109.8,8,8,0,0,0-10-10,104.84,104.84,0,0,0-52.91,37A104,104,0,0,0,136,224a103.09,103.09,0,0,0,62.52-20.88,104.84,104.84,0,0,0,37-52.91A8,8,0,0,0,233.54,142.23ZM188.9,190.34A88,88,0,0,1,65.66,67.11a89,89,0,0,1,31.4-26A106,106,0,0,0,96,56,104.11,104.11,0,0,0,200,160a106,106,0,0,0,14.92-1.06A89,89,0,0,1,188.9,190.34Z"/>',
  bell:           '<path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z"/>',
  eye:            '<path d="M247.31,124.76c-.35-.79-8.82-19.58-27.65-38.41C194.57,61.26,162.88,48,128,48S61.43,61.26,36.34,86.35C17.51,105.18,9,124,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208s66.57-13.26,91.66-38.34c18.83-18.83,27.3-37.61,27.65-38.4A8,8,0,0,0,247.31,124.76ZM128,192c-30.78,0-57.67-11.19-79.93-33.25A133.47,133.47,0,0,1,25,128,133.33,133.33,0,0,1,48.07,97.25C70.33,75.19,97.22,64,128,64s57.67,11.19,79.93,33.25A133.46,133.46,0,0,1,231.05,128C223.84,141.46,192.43,192,128,192Zm0-112a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Z"/>',
  megaphone:      '<path d="M248,120a48.05,48.05,0,0,0-48-48H160.2c-2.91-.17-53.62-3.74-101.91-44.24A16,16,0,0,0,32,40V200a16,16,0,0,0,26.29,12.25c37.77-31.68,77-40.76,93.71-43.3v31.72A16,16,0,0,0,159.12,214l11,7.33A16,16,0,0,0,194.5,212l11.77-44.36A48.07,48.07,0,0,0,248,120ZM48,199.93V40h0c42.81,35.91,86.63,45,104,47.24v65.48C134.65,155,90.84,164.07,48,199.93Zm131,8,0,.11-11-7.33V168h21.6ZM200,152H168V88h32a32,32,0,1,1,0,64Z"/>',
  microphone:     '<path d="M128,176a48.05,48.05,0,0,0,48-48V64a48,48,0,0,0-96,0v64A48.05,48.05,0,0,0,128,176ZM96,64a32,32,0,0,1,64,0v64a32,32,0,0,1-64,0Zm40,143.6V240a8,8,0,0,1-16,0V207.6A80.11,80.11,0,0,1,48,128a8,8,0,0,1,16,0,64,64,0,0,0,128,0,8,8,0,0,1,16,0A80.11,80.11,0,0,1,136,207.6Z"/>',
  eyeSlash:       '<path d="M53.92,34.62A8,8,0,1,0,42.08,45.38L61.32,66.55C25,88.84,9.38,123.2,8.69,124.76a8,8,0,0,0,0,6.5c.35.79,8.82,19.57,27.65,38.4C61.43,194.74,93.12,208,128,208a127.11,127.11,0,0,0,52.07-10.83l22,24.21a8,8,0,1,0,11.84-10.76Zm47.33,75.84,41.67,45.85a32,32,0,0,1-41.67-45.85ZM128,192c-30.78,0-57.67-11.19-79.93-33.25A133.16,133.16,0,0,1,25,128c4.69-8.79,19.66-33.39,47.35-49.38l18,19.75a48,48,0,0,0,63.66,70l14.73,16.2A112,112,0,0,1,128,192Zm6-95.43a8,8,0,0,1,3-15.72,48.16,48.16,0,0,1,38.77,42.64,8,8,0,0,1-7.22,8.71,6.39,6.39,0,0,1-.75,0,8,8,0,0,1-8-7.26A32.09,32.09,0,0,0,134,96.57Zm113.28,34.69c-.42.94-10.55,23.37-33.36,43.8a8,8,0,1,1-10.67-11.92A132.77,132.77,0,0,0,231.05,128a133.15,133.15,0,0,0-23.12-30.77C185.67,75.19,158.78,64,128,64a118.37,118.37,0,0,0-19.36,1.57A8,8,0,1,1,106,49.79,134,134,0,0,1,128,48c34.88,0,66.57,13.26,91.66,38.35,18.83,18.83,27.3,37.62,27.65,38.41A8,8,0,0,1,247.31,131.26Z"/>',
};

// Shakllar <g fill stroke=none> ichida: eski CSS qoidalaridagi stroke (chiziqli ikonkalar davridan) ularga ta'sir qilmaydi
function icon(name) {
  const body = ICONS[name];
  return body
    ? `<svg class="ico" viewBox="0 0 256 256" aria-hidden="true"><g fill="currentColor" stroke="none">${body}</g></svg>`
    : '';
}

// HTML ichidagi belgilarni to'ldiradi:
// <span data-icon="..."></span> — ichiga SVG qo'yiladi;
// <svg data-icon="..." width height class></svg> — elementning o'zi qoladi (o'lchami, klassi, display holati), faqat
// shakli to'ldiriladi. Ko'z (eye-show/eye-hide) va mavzu tugmalarida JS shu elementlarni yashirib-ko'rsatadi
function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => {
    if (el instanceof SVGSVGElement) {
      el.setAttribute('viewBox', '0 0 256 256');
      el.innerHTML = `<g fill="currentColor" stroke="none">${ICONS[el.dataset.icon] || ''}</g>`;
    } else {
      el.innerHTML = icon(el.dataset.icon);
    }
  });
}
hydrateIcons();

// ==========================================
// CSRF HIMOYASI — Django xavfsizligi
// ==========================================

/**
 * Django tomonidan o'rnatilgan 'csrftoken' cookie'sini o'qib olish.
 * Bu token barcha POST/PUT/PATCH/DELETE so'rovlarga qo'shilishi shart.
 */
function getCsrfToken() {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith('csrftoken=')) {
      return decodeURIComponent(cookie.substring('csrftoken='.length));
    }
  }
  return '';
}

/**
 * Global fetch() ni intercept qilib, barcha mutatsiya so'rovlariga
 * (POST, PUT, PATCH, DELETE) avtomatik X-CSRFToken header qo'shadi.
 * GET va HEAD so'rovlarga tegmaydi.
 */
const _originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET' && method !== 'HEAD') {
    options.headers = {
      ...(options.headers || {}),
      'X-CSRFToken': getCsrfToken(),
    };
  }
  const response = await _originalFetch.call(window, url, options);
  if (response.status === 401 && typeof url === 'string' && !url.includes('/auth/')) {
    checkAuth();
  }
  return response;
};

// ==========================================
// TUGMALAR: data-action (Content-Security-Policy inline onclick="..." ni bajarmaydi)
// ==========================================
// <button data-action="openModal" data-args='["modalIncome"]'> bosilganda openModal("modalIncome") chaqiriladi.
// data-stop — bosish ota elementlarga o'tmaydi (oldingi event.stopPropagation() o'rniga).
// Capture bosqichida ushlanadi: ota elementlarning o'z click listenerlaridan oldin ishlaydi
const CLICK_ACTIONS = {
  openTxPage, openDebtsPage, openRatesPage, openWalletsPage, openHomeListPage, loadRatesPage, closeTxPage, goHome, openTxDetail, closeTxDetail,
  openModal, closeModal, openCategoryManager, openWeekdayTxFilter,
  openRepayModal, deleteDebt, deleteWallet, deleteMember, openEditWallet, loadWalletPageData,
  openRecurringModal, deleteRecurring, openGoalModal, deleteGoal, fundGoal,
  loadMonthlyStats: _loadMonthlyStats, goToListPage,
};

document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-action]');
  const action = el && CLICK_ACTIONS[el.dataset.action];
  if (!action) return;
  if (el.hasAttribute('data-stop')) e.stopPropagation();
  let args = [];
  try {
    args = el.dataset.args ? JSON.parse(el.dataset.args) : [];
  } catch (err) {
    console.error('data-args noto\'g\'ri:', el.dataset.args);
    return;
  }
  action(...args);
}, true);

// data-args qiymatini HTML atributiga xavfsiz yozish (matnli argumentlar uchun)
function actionArgs(...args) {
  return escapeHtml(JSON.stringify(args));
}

// ==========================================
// BO'LIM RO'YXATLARINI SAHIFALASH
// ==========================================
// Ro'yxatlar to'liq yuklanadi (bir nechta API dan birlashtirilib, sana bo'yicha saralanadi), shuning uchun
// sahifalarga brauzerda bo'linadi — server sahifalashi turli manbalar orasidagi tartibni buzardi.
// Har bir sahifada 10 tadan yozuv
const LIST_PAGE_SIZE = 10;
const LIST_PAGERS = {
  tx:     { size: LIST_PAGE_SIZE, page: 1, pagerId: 'txPagePager',     listId: 'txPageList',     render: () => renderTxPageList() },
  debts:  { size: LIST_PAGE_SIZE, page: 1, pagerId: 'debtPagePager',   listId: 'debtPageList',   render: () => renderDebtPageList() },
  wallet: { size: LIST_PAGE_SIZE, page: 1, pagerId: 'walletPagePager', listId: 'walletPageList', render: () => renderWalletPage() },
  rates:  { size: LIST_PAGE_SIZE, page: 1, pagerId: 'ratesPagePager',  listId: 'ratesTable',     render: () => renderRatesTable() },
};

// Bo'lim ochilganda, filtr yoki oy almashganda ro'yxat birinchi sahifadan boshlanadi
function resetListPage(key) {
  LIST_PAGERS[key].page = 1;
}

function clearListPager(key) {
  const el = document.getElementById(LIST_PAGERS[key].pagerId);
  if (el) el.innerHTML = '';
}

// Joriy sahifadagi qism. Yozuv o'chirilib sahifa kamaysa — oxirgi mavjud sahifaga tushadi
function pageSlice(key, items) {
  const p = LIST_PAGERS[key];
  const pages = Math.max(1, Math.ceil(items.length / p.size));
  p.page = Math.min(Math.max(1, p.page), pages);
  _renderListPager(key, items.length, pages);
  const start = (p.page - 1) * p.size;
  return items.slice(start, start + p.size);
}

// Paginator "‹ 2 ›": oldingi sahifa, joriy sahifa raqami, keyingi sahifa
function _renderListPager(key, total, pages) {
  const p = LIST_PAGERS[key];
  const el = document.getElementById(p.pagerId);
  if (!el) return;
  if (pages <= 1) { el.innerHTML = ''; return; }

  const pageBtn = (page, content, attrs = '') =>
    `<button type="button" class="list-pager-btn" data-action="goToListPage" data-args="${actionArgs(key, page)}" ${attrs}>${content}</button>`;
  el.innerHTML = `
    <div class="list-pager-controls">
      ${pageBtn(p.page - 1, icon('chevronLeft'), `aria-label="Oldingi sahifa"${p.page === 1 ? ' disabled' : ''}`)}
      <span class="list-pager-btn is-current" aria-current="page" aria-label="${p.page}-sahifa, jami ${pages}" tabindex="-1">${p.page}</span>
      ${pageBtn(p.page + 1, icon('chevronRight'), `aria-label="Keyingi sahifa"${p.page === pages ? ' disabled' : ''}`)}
    </div>`;
}

function goToListPage(key, page) {
  const p = LIST_PAGERS[key];
  if (!p) return;
  const pager = document.getElementById(p.pagerId);
  const focusWasInPager = !!pager?.contains(document.activeElement);
  p.page = page;
  p.render();
  // Klaviatura bilan ishlaganda fokus yo'qolmaydi: qayta chizilgan paginatordagi joriy sahifaga o'tadi
  if (focusWasInPager) pager.querySelector('.is-current')?.focus();

  // Yangi sahifa ro'yxat boshidan ko'rinadi — pastdagi paginator bosilganda sahifa tepaga qaytadi
  const body = document.getElementById('txPageScrollBody');
  const header = document.getElementById(p.listId)?.previousElementSibling;
  if (!body || !header) return;
  const top = header.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop - 12;
  if (top < body.scrollTop) {
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    body.scrollTo({ top, behavior: smooth ? 'smooth' : 'auto' });
  }
}

// Global state
let state = {
  summary: {},
  wallets: [],
  members: [],
  incomeCategories: [],
  expenseCategories: [],
  expenses: [],
  incomes: [],
  transfers: [],
  debts: [],
  recurring: [],
  goals: [],
  currentUser: null,
  currentUserId: null,
  txLimit: 15,
};

// Utilities
function formatMoney(amount, currency = 'UZS') {
  return formatNumber(amount) + ' ' + currency;
}

// Summa maydonini o'qiydi: 2 xonagacha kasr (sent/tiyin). Server ham 2 xonadan ortig'ini rad etadi —
// bu yerda yaxlitlash faqat JS kasr xatosini (0.1 + 0.2) olib tashlaydi. Bo'sh yoki noto'g'ri bo'lsa NaN
function readAmount(id) {
  const raw = String(document.getElementById(id)?.value ?? '').trim().replace(',', '.');
  if (!raw) return NaN;
  const n = Number(raw);
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : NaN;
}

// Miqdor maydonlari (data-amount): yozilayotganda xonalarga ajraladi — 10 000, 1 000 000, 12 650,45.
// type="number" bo'sh joy ko'rsatolmaydi, shuning uchun maydon matnli; lekin el.value o'qilganda toza son ("1000000"),
// yozilganda (el.value = 35000.00) o'zi formatlanadi — readAmount() va qolgan kod o'zgarmaydi
const _nativeValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
const AMOUNT_MAX_DIGITS = 13;  // server chegarasi 10^12

function amountRaw(text) {
  return String(text ?? '').replace(/\s/g, '').replace(',', '.');
}

// Yozilgan matn -> ko'rinish: faqat raqam va bitta kasr belgisi (2 xonagacha), butun qismi uchtadan ajratiladi
function formatAmountText(text) {
  let s = String(text ?? '').replace(/[^\d.,]/g, '');
  const sep = s.search(/[.,]/);
  let whole = sep < 0 ? s : s.slice(0, sep);
  const frac = sep < 0 ? null : s.slice(sep + 1).replace(/[.,]/g, '').slice(0, 2);
  whole = whole.replace(/^0+(?=\d)/, '').slice(0, AMOUNT_MAX_DIGITS);
  if (frac !== null && !whole) whole = '0';
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  return frac === null ? grouped : `${grouped},${frac}`;
}

// Dasturdan berilgan son (serverdan "35000.00") — ortiqcha nollarsiz
function formatAmountValue(value) {
  const raw = amountRaw(value);
  if (raw === '') return '';
  const n = Number(raw);
  if (!Number.isFinite(n)) return formatAmountText(raw);
  const fixed = Math.round(n * 100) % 100 === 0 ? String(Math.trunc(n)) : n.toFixed(2);
  return formatAmountText(fixed);
}

// type="number" dagi min/max tekshiruvi o'rniga: noto'g'ri bo'lsa forma yuborilmaydi va brauzer xabar ko'rsatadi
function validateAmountInput(el) {
  const raw = el.value;
  const n = Number(raw);
  let msg = '';
  if (raw && !Number.isFinite(n)) msg = 'Faqat son kiriting';
  else if (raw && el.min !== '' && n < Number(el.min)) msg = Number(el.min) > 0 ? "Miqdor 0 dan katta bo'lsin" : "Miqdor manfiy bo'lmasin";
  else if (raw && el.max !== '' && n > Number(el.max)) msg = `Miqdor ${formatNumber(el.max)} dan oshmasin`;
  el.setCustomValidity(msg && (window.i18n?.t(msg) || msg));
}

// Majburiy maydon to'ldirilmasa brauzerning oddiy pufagi o'rniga: qizil ramka va maydon tagida izoh.
// `invalid` hodisasi ko'tarilmaydi — shuning uchun capture bosqichida butun hujjatdan ushlanadi
// Maxsus dropdown (custom-select) da haqiqiy <select> yashirin: qizil ramka va izoh uning tugmasi/o'rami bilan bog'lanadi
const fieldVisual = (el) => el.closest('.custom-select-wrapper')?.querySelector('.custom-select-trigger') || el;
const fieldAnchor = (el) => el.closest('.custom-select-wrapper') || el;

function clearFieldError(el) {
  fieldVisual(el).classList.remove('field-invalid');
  el.classList.remove('field-invalid');
  el.removeAttribute('aria-invalid');
  const msg = el._errEl;
  if (msg) { msg.remove(); el._errEl = null; }
}

let _invalidFocusPending = false;
document.addEventListener('invalid', (e) => {
  const el = e.target;
  if (!(el instanceof HTMLElement) || !el.classList.contains('form-control')) return;
  e.preventDefault();
  const tr = (s) => window.i18n?.t(s) || s;
  // Brauzerning o'z xabari (validationMessage) brauzer tilida chiqadi — ilova tilida o'zimiz yozamiz.
  // customError xabarlarini (miqdor tekshiruvi) ilovaning o'zi allaqachon tarjima qilgan
  const vs = el.validity;
  const isDate = el.type === 'date';
  let text;
  if (vs.valueMissing) text = tr("Bo'limni to'ldiring");
  else if (vs.customError) text = el.validationMessage;
  else if (vs.badInput) text = tr(isDate ? "Sanani to'g'ri kiriting" : "Noto'g'ri qiymat");
  else if (vs.rangeUnderflow || vs.rangeOverflow) text = tr(isDate ? "Sana ruxsat etilgan oraliqdan tashqarida" : "Qiymat ruxsat etilgan oraliqdan tashqarida");
  else if (vs.tooShort) text = `${tr('Kamida belgilar soni:')} ${el.minLength}`;
  else if (vs.typeMismatch) text = tr(el.type === 'email' ? "Elektron pochtani to'g'ri kiriting" : "Noto'g'ri format");
  else text = tr("Noto'g'ri qiymat");
  if (!el._errEl) {
    const msg = document.createElement('div');
    msg.className = 'field-error-msg';
    msg.setAttribute('role', 'alert');
    fieldAnchor(el).insertAdjacentElement('afterend', msg);
    el._errEl = msg;
    const clear = () => {
      // checkValidity() noto'g'ri maydonda `invalid` hodisasini qayta chiqarib, har bosishda fokus/scrollni chaqirardi
      if (el.validity.valid) {
        clearFieldError(el);
        el.removeEventListener('input', clear);
        el.removeEventListener('change', clear);
      }
    };
    el.addEventListener('input', clear);
    el.addEventListener('change', clear);
  }
  el._errEl.textContent = text;
  const visual = fieldVisual(el);
  visual.classList.add('field-invalid');
  el.classList.add('field-invalid');
  el.setAttribute('aria-invalid', 'true');
  // Birinchi to'ldirilmagan maydonga o'tiladi (brauzer pufagi o'chirilgani uchun o'zimiz fokus beramiz)
  if (!_invalidFocusPending) {
    _invalidFocusPending = true;
    visual.focus({ preventScroll: false });
    visual.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
    setTimeout(() => { _invalidFocusPending = false; }, 0);
  }
}, true);
// Forma tozalansa yoki oyna qayta ochilsa eski xatolar qolmasin
document.addEventListener('reset', (e) => {
  e.target.querySelectorAll?.('.field-invalid').forEach(clearFieldError);
}, true);

function enhanceAmountInput(el) {
  Object.defineProperty(el, 'value', {
    configurable: true,
    get() { return amountRaw(_nativeValue.get.call(el)); },
    set(v) {
      _nativeValue.set.call(el, formatAmountValue(v));
      validateAmountInput(el);
    },
  });
  // Xona orasidagi bo'sh joyni o'chirish befoyda (darhol qaytadi) — Backspace/Delete undan keyingi raqamni o'chiradi
  el.addEventListener('keydown', (e) => {
    if ((e.key !== 'Backspace' && e.key !== 'Delete') || el.selectionStart !== el.selectionEnd) return;
    const shown = _nativeValue.get.call(el);
    const pos = el.selectionStart;
    if (e.key === 'Backspace' && shown[pos - 1] === ' ') el.setSelectionRange(pos - 1, pos - 1);
    if (e.key === 'Delete' && shown[pos] === ' ') el.setSelectionRange(pos + 1, pos + 1);
  });
  el.addEventListener('input', () => {
    const shown = _nativeValue.get.call(el);
    // Kursor joyi: undan chapdagi raqam/kasr belgilari soni saqlanadi (bo'sh joylar qo'shilsa ham siljimaydi)
    const caret = el.selectionStart ?? shown.length;
    const keep = shown.slice(0, caret).replace(/[^\d.,]/g, '').length;
    const formatted = formatAmountText(shown);
    if (formatted !== shown) {
      _nativeValue.set.call(el, formatted);
      let pos = 0;
      for (let seen = 0; pos < formatted.length && seen < keep; pos++) {
        if (/[\d,]/.test(formatted[pos])) seen++;
      }
      try { el.setSelectionRange(pos, pos); } catch (e) { /* fokussiz maydon */ }
    }
    validateAmountInput(el);
  });
  el.value = _nativeValue.get.call(el);  // HTML dagi boshlang'ich qiymat (value="100") ham formatlansin
}
document.querySelectorAll('input[data-amount]').forEach(enhanceAmountInput);

// Har xil valyutadagi summalarni qo'shib bo'lmaydi: { UZS: 1000, USD: 5 } -> "1 000 UZS + 5 USD"
function sumByCurrency(items, amountOf, currencyOf) {
  const totals = {};
  items.forEach(x => {
    const cur = currencyOf(x) || 'UZS';
    totals[cur] = (totals[cur] || 0) + Number(amountOf(x) || 0);
  });
  return totals;
}

function formatCurrencyTotals(totals) {
  const entries = Object.entries(totals).sort(([a], [b]) => (a !== 'UZS') - (b !== 'UZS') || a.localeCompare(b));
  if (!entries.length) return '0 UZS';
  return entries.map(([cur, total]) => `${formatNumber(total)} ${escapeHtml(cur)}`).join(' + ');
}

// "1 USD = 11 809,19 UZS" (kurs 1 dan kichik bo'lsa teskarisi ko'rsatiladi: 1 USD = ... UZS)
function formatRateText(fromCur, toCur, rate) {
  if (!rate) return '';
  const fmt = n => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n).replace(/,/g, ' ');
  return rate >= 1 ? `1 ${fromCur} = ${fmt(rate)} ${toCur}` : `1 ${toCur} = ${fmt(1 / rate)} ${fromCur}`;
}

// Valyutalari har xil hamyonlar o'rtasidagi o'tkazma: "100 USD → 1 180 919 UZS"
function transferAmountText(t) {
  if (!t.from_currency || !t.to_currency || t.from_currency === t.to_currency) return null;
  return `${formatNumber(t.summa)} ${t.from_currency} → ${formatNumber(t.to_summa)} ${t.to_currency}`;
}

// Summa valyutasi bilan: "20 000 UZS", "100 USD" (valyuta noma'lum bo'lsa faqat son)
function amountWithCurrency(amount, currency) {
  return currency ? `${formatNumber(amount)} ${currency}` : formatNumber(amount);
}

// Statistikadagi toifa asl valyutada bo'lsa: "100 USD ≈ " (keyin so'mdagi qiymat keladi)
function statsOriginalAmountHtml(parts, statsCur) {
  if (!parts || !parts.length || parts.every(p => p.currency === statsCur)) return '';
  const text = parts.map(p => `${formatNumber(p.total)} ${escapeHtml(p.currency)}`).join(' + ');
  return `<span class="stats-cat-orig">${text} ≈</span> `;
}

// Kursi topilmagan valyuta statistikaga qo'shilmaydi — foydalanuvchini bir marta ogohlantiramiz
const _warnedMissingRates = new Set();
function warnMissingRates(codes) {
  const fresh = (codes || []).filter(c => !_warnedMissingRates.has(c));
  if (!fresh.length) return;
  fresh.forEach(c => _warnedMissingRates.add(c));
  showToast(`${fresh.join(', ')} kursini aniqlab bo'lmadi — bu valyutadagi miqdorlar hisobotga qo'shilmadi`, 'error');
}

function debtCurrency(d) {
  return escapeHtml(d.currency || 'UZS');
}

// Brauzerlarda o'zbekcha oy nomlari yo'q: toLocaleDateString('uz-UZ') "2026 M10 11" qaytaradi, shuning uchun sanani o'zimiz yozamiz.
// Oy nomlari va sana tartibi tanlangan interfeys tilidan olinadi (i18n.js)
const UZ_MONTHS = window.i18n?.months || [
  'Yanvar','Fevral','Mart','Aprel','May','Iyun',
  'Iyul','Avgust','Sentabr','Oktabr','Noyabr','Dekabr'
];
const UZ_MONTHS_SHORT = ['yan','fev','mar','apr','may','iyn','iyl','avg','sen','okt','noy','dek'];

// "11-oktabr", { year: true } -> "11-oktabr, 2026", { year: true, time: true } -> "11-oktabr, 2026, 21:47"
function formatUzDate(value, { year = false, time = false } = {}) {
  if (!value) return '';
  const d = new Date(value);
  if (isNaN(d)) return '';
  let s;
  if (window.i18n) s = i18n.formatDate(d.getDate(), d.getMonth(), { year: year && d.getFullYear() });
  else {
    s = `${d.getDate()}-${UZ_MONTHS[d.getMonth()].toLowerCase()}`;
    if (year) s += `, ${d.getFullYear()}`;
  }
  if (time) s += `, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return s;
}

// Qarz muddati ("2026-10-20" — vaqtsiz sana) -> "20-oktabr, 2026". Mahalliy yarim tun deb o'qiladi:
// aks holda UTC dan orqadagi vaqt zonalarida bir kun oldingi sana chiqardi
function formatDueDate(debt) {
  return debt.due_date ? formatUzDate(`${debt.due_date}T00:00:00`, { year: true }) : '';
}

// Ro'yxatlar uchun qisqa sana: "11-okt"
function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  if (window.i18n) return i18n.formatDate(d.getDate(), d.getMonth(), { short: true });
  return `${d.getDate()}-${UZ_MONTHS_SHORT[d.getMonth()]}`;
}

// Ilovaning o'z tasdiqlash oynasi (brauzerning standart oynasi o'rniga). true / false bilan hal bo'ladigan Promise qaytaradi
let _confirmResolver = null;

function showConfirm({ title = 'Tasdiqlang', message = '', confirmText = 'Ha', cancelText = "Yo'q", danger = true } = {}) {
  return new Promise(resolve => {
    if (_confirmResolver) _confirmResolver(false);
    _confirmResolver = resolve;

    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmIcon').innerHTML = icon(danger ? 'warning' : 'check');
    document.getElementById('confirmIcon').classList.toggle('danger', danger);
    const okBtn = document.getElementById('btnConfirmOk');
    okBtn.textContent = confirmText;
    okBtn.className = danger ? 'btn btn-rose' : 'btn btn-primary';
    document.getElementById('btnConfirmCancel').textContent = cancelText;

    openModal('modalConfirm');
    document.getElementById('btnConfirmCancel').focus();
  });
}

function _resolveConfirm(value) {
  closeModal('modalConfirm');
  const resolve = _confirmResolver;
  _confirmResolver = null;
  if (resolve) resolve(value);
}

document.getElementById('btnConfirmOk')?.addEventListener('click', () => _resolveConfirm(true));
document.getElementById('btnConfirmCancel')?.addEventListener('click', () => _resolveConfirm(false));
document.getElementById('modalConfirm')?.addEventListener('click', (e) => {
  if (e.target.id === 'modalConfirm') _resolveConfirm(false);
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && document.getElementById('modalConfirm')?.classList.contains('active')) {
    e.preventDefault(); // Esc faqat tasdiq oynasini yopadi, ostidagi oynani emas
    _resolveConfirm(false);
  }
});

// Har qanday o'chirishdan oldin bitta tasdiq oynasi chiqadi: "Ha" bosilsa o'chiriladi
function confirmDelete(message) {
  return showConfirm({
    title: "O'chirilsinmi?",
    message,
    confirmText: "Ha, o'chirish",
    cancelText: "Yo'q",
  });
}

// Forma yuborilayotganda saqlash tugmasi o'chib turadi va qayta yuborish e'tiborsiz qoladi:
// tugma tez ikki bosilsa (yoki Enter) harajat/kirim ikki marta yozilib, balans ikki marta o'zgarmasin
function onSubmitOnce(formId, handler) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (form.dataset.busy) return;
    form.dataset.busy = '1';
    const buttons = form.querySelectorAll('button[type="submit"]');
    buttons.forEach(b => { b.disabled = true; });
    try {
      await handler(e);
    } finally {
      delete form.dataset.busy;
      buttons.forEach(b => { b.disabled = false; });
    }
  });
}

// So'rov serverga umuman yetib bormaganda (server o'chiq, internet yo'q) chiqadigan xabar
const NETWORK_ERROR_MESSAGE = "Serverga ulanib bo'lmadi. Internet aloqasini yoki server ishlayotganini tekshiring.";

// action — xabar yonidagi tugma ({ label, onClick }), masalan o'chirilgan operatsiyani qaytarish.
// Tugmali xabar uzoqroq turadi: foydalanuvchi o'qib, bosishga ulgursin
function showToast(message, type = 'success', { action, duration } = {}) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const iconEl = document.createElement('span');
  iconEl.innerHTML = type === 'success' ? icon('check') : icon('warning');
  const textEl = document.createElement('div');
  textEl.textContent = message;
  toast.append(iconEl, textEl);

  const hide = () => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  };
  if (action) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'toast-action';
    btn.textContent = action.label;
    btn.addEventListener('click', () => {
      btn.disabled = true;
      hide();
      action.onClick();
    }, { once: true });
    toast.appendChild(btn);
  }
  container.appendChild(toast);

  setTimeout(hide, duration || (action ? 7000 : 3500));
}

// Hamyon sahifasi holati
let _walletPageId = null;
let _walletPageFilter = 'all';
let _walletPageData = null;

function getCurrentDateLocal() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

// Formada faqat sana tanlanadi; bir kundagi yozuvlar tartibi buzilmasligi uchun hozirgi vaqt qo'shib yuboriladi
function dateInputToISO(dateVal) {
  const [y, m, d] = dateVal.split('-').map(Number);
  const dt = new Date();
  dt.setFullYear(y, m - 1, d);
  return dt.toISOString();
}

// Xotira (localStorage) yopiq bo'lishi mumkin (maxfiy rejim, bloklangan sayt ma'lumotlari) —
// u holda sozlama faqat shu safarga qo'llanadi, skript yiqilmaydi
function storageGet(key) {
  try { return localStorage.getItem(key); } catch (e) { return null; }
}
function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (e) { /* faqat shu safarga qo'llanadi */ }
}

// Balance hide/show toggle (fintech-style privacy)
const BALANCE_HIDDEN_KEY = 'moliyaBalanceHidden';
// Holat xotirada ham saqlanadi — localStorage yozilmasa ham tugma ishlayveradi
let balanceHidden = storageGet(BALANCE_HIDDEN_KEY) === '1';
function applyBalanceVisibility() {
  const hidden = balanceHidden;
  const sumEl = document.getElementById('heroBalanceSum');
  const btn = document.getElementById('btnToggleBalance');
  if (!sumEl || !btn) return;
  sumEl.classList.toggle('balance-hidden', hidden);
  document.getElementById('heroWalletList')?.classList.toggle('balance-hidden', hidden);
  document.getElementById('heroBalanceExtra')?.classList.toggle('balance-hidden', hidden);
  const eyeShow = btn.querySelector('.eye-show');
  const eyeHide = btn.querySelector('.eye-hide');
  if (eyeShow && eyeHide) {
    eyeShow.style.display = hidden ? 'none' : 'block';
    eyeHide.style.display = hidden ? 'block' : 'none';
  }
  btn.title = hidden ? "Qoldiqni ko'rsatish" : 'Qoldiqni yashirish';
}
document.getElementById('btnToggleBalance')?.addEventListener('click', () => {
  balanceHidden = !balanceHidden;
  storageSet(BALANCE_HIDDEN_KEY, balanceHidden ? '1' : '0');
  applyBalanceVisibility();
});
applyBalanceVisibility();

// ==========================================
// YORUG' / QORONG'U REJIM (Light / Dark theme)
// ==========================================
const THEME_KEY = 'moliyaTheme';

function applyThemeIcon(theme) {
  const btn = document.getElementById('btnThemeToggle');
  if (!btn) return;
  const sun = btn.querySelector('.theme-ico-sun');
  const moon = btn.querySelector('.theme-ico-moon');
  if (sun && moon) {
    sun.style.display = theme === 'dark' ? 'none' : 'block';
    moon.style.display = theme === 'dark' ? 'block' : 'none';
  }
  btn.title = theme === 'dark' ? "Yorug' rejimga o'tish" : "Qorong'u rejimga o'tish";
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  storageSet(THEME_KEY, theme);
  applyThemeIcon(theme);
}

document.getElementById('btnThemeToggle')?.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  setTheme(current === 'dark' ? 'light' : 'dark');
});

applyThemeIcon(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');

// ==========================================
// RANG MAVZUSI (Sozlamalar → Ranglar) — faqat ranglar almashadi, shrift o'zgarmaydi.
// Standart — "oltin". "moy" — klassik moy-yashil: atributsiz (style.css :root ranglari), lekin tanlov saqlanadi,
// aks holda keyingi safar standart oltin qaytib qolardi. Ro'yxat theme-init.js dagi bilan bir xil
// ==========================================
const PALETTE_KEY = 'moliyaPalette';
const DEFAULT_PALETTE = 'oltin';
const CLASSIC_PALETTE = 'moy';
const PALETTES = ['oltin', 'zumrad', 'firuza', 'lojuvard', 'zaytun', 'olcha'];

function setPalette(palette) {
  const value = palette === CLASSIC_PALETTE || PALETTES.includes(palette) ? palette : DEFAULT_PALETTE;
  if (value === CLASSIC_PALETTE) document.documentElement.removeAttribute('data-palette');
  else document.documentElement.setAttribute('data-palette', value);
  try { localStorage.setItem(PALETTE_KEY, value); } catch (e) { /* faqat shu safarga qo'llanadi */ }
}

document.querySelectorAll('input[name="palette"]').forEach(radio => {
  radio.checked = radio.value === (document.documentElement.getAttribute('data-palette') || CLASSIC_PALETTE);
  radio.addEventListener('change', () => setPalette(radio.value));
});

// INTERFEYS TILI (Sozlamalar → Til) — tanlov i18n.js ga beriladi, u sahifani yangi tilda qayta yuklaydi
document.querySelectorAll('input[name="language"]').forEach(radio => {
  radio.checked = radio.value === (window.i18n?.lang || 'uz');
  radio.addEventListener('change', () => window.i18n?.setLang(radio.value));
});

// Modal open/close helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    // Yopilganda fokus shu oynani ochgan tugmaga qaytadi (klaviatura bilan ishlaganda joy yo'qolmasin)
    if (!el.classList.contains('active')) {
      el._returnFocus = document.activeElement;
      el.querySelectorAll('.field-invalid').forEach(clearFieldError);
    }
    el.classList.add('active');
    if (id === 'modalExpense') {
      const expDate = document.getElementById('expenseDate');
      if (expDate && !expDate.value) expDate.value = getCurrentDateLocal();
    }
    if (id === 'modalIncome') {
      const incDate = document.getElementById('incomeDate');
      if (incDate && !incDate.value) incDate.value = getCurrentDateLocal();
    }
    if (id === 'modalTransfer') updateTransferCurrencyPreview();
    if (id === 'modalDebt') updateDebtCurrencyField();
    if (id === 'modalExpense' || id === 'modalIncome') updateAmountLabels();
    focusFirstField(el);
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const hadFocus = el.contains(document.activeElement);
  el.classList.remove('active');
  if (id === 'modalTransfer') unlockTransferTarget();
  if (el._onClose) el._onClose();
  if (hadFocus && el._returnFocus && document.contains(el._returnFocus)) el._returnFocus.focus();
  el._returnFocus = null;
}

// Close modal when clicking outside. Bosish ham, qo'yib yuborish ham fonda bo'lsa yopiladi: maydondagi matnni
// belgilab sichqonchani oyna tashqarisida qo'yib yuborish oynani yopib, yozilganni yo'qotmasin
let _downOnBackdrop = false;
window.addEventListener('mousedown', (e) => {
  _downOnBackdrop = !!e.target.classList?.contains('modal-backdrop');
}, true);
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop') && _downOnBackdrop) closeModal(e.target.id);
});

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function _visibleFocusables(root) {
  return [...root.querySelectorAll(FOCUSABLE)].filter(el => el.offsetParent !== null || el === document.activeElement);
}

// Kompyuterda oyna ochilganda birinchi maydonga fokus o'tadi. Telefonda emas — klaviatura o'z-o'zidan ochilib ketmasin
function focusFirstField(el) {
  if (!window.matchMedia('(pointer: fine)').matches) return;
  setTimeout(() => {
    if (!el.classList.contains('active') || el.contains(document.activeElement)) return; // chaqiruvchi o'zi fokuslagan (masalan tasdiq oynasi)
    const fields = _visibleFocusables(el).filter(f => !f.classList.contains('modal-close'));
    (fields.find(f => f.matches('input, textarea, .custom-select-trigger')) || fields[0])?.focus();
  }, 0);
}

// Oynalar ekran o'quvchilar uchun "dialog" deb belgilanadi, sarlavhasi uning nomi bo'ladi
document.querySelectorAll('.modal-backdrop').forEach(bd => {
  const win = bd.querySelector('.modal-window');
  if (!win || bd.getAttribute('role') || win.getAttribute('role')) return;
  win.setAttribute('role', 'dialog');
  win.setAttribute('aria-modal', 'true');
  const title = win.querySelector('.modal-header h3');
  if (title) {
    if (!title.id) title.id = `${bd.id}Title`;
    win.setAttribute('aria-labelledby', title.id);
  }
});

// Eng ustdagi ochiq oyna (bir nechtasi ochiq bo'lsa — z-index kattasi)
function _topModal() {
  const open = [...document.querySelectorAll('.modal-backdrop.active')];
  const z = el => parseInt(getComputedStyle(el).zIndex, 10) || 0;
  return open.sort((a, b) => z(b) - z(a))[0] || null;
}

// Sahifa ustidagi qatlam (oyna yoki tafsilot): fokus uning ichida aylanadi, "orqaga" avval uni yopadi
function _activeDialogLayer() {
  const detail = document.getElementById('txDetailBackdrop');
  return _topModal() || (detail?.classList.contains('active') ? detail : null);
}

// Tab — fokus ochiq oyna ichida qoladi, orqadagi sahifaga o'tib ketmaydi.
// Esc — eng ustdagi qatlamni yopadi: ochiq tanlov ro'yxati -> oyna -> tafsilot -> bo'lim sahifasi.
// Tasdiq oynasi, xabarlar va davr panellari o'z ishlovchilarida yopiladi (ular preventDefault qiladi)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    const layer = _activeDialogLayer();
    if (!layer) return;
    const items = _visibleFocusables(layer);
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (!layer.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    return;
  }
  if (e.key !== 'Escape' || e.defaultPrevented) return;
  // Bu ishlovchi ulardan oldin ro'yxatdan o'tgan — shuning uchun holatini o'zi tekshiradi
  if (document.getElementById('modalConfirm')?.classList.contains('active')
      || document.getElementById('notifPanel')?.hidden === false
      || document.getElementById('periodPanel')?.hidden === false) return;
  if (document.querySelector('.custom-select-panel.open')) {
    document.querySelectorAll('.custom-select-panel.open, .custom-select-wrapper.open').forEach(x => x.classList.remove('open'));
    return;
  }
  const modal = _topModal();
  if (modal) { closeModal(modal.id); return; }
  if (document.getElementById('txDetailBackdrop')?.classList.contains('active')) { closeTxDetail(); return; }
  if (document.getElementById('txPageOverlay')?.classList.contains('open')) closeTxPage();
});

// Oyna, bo'lim sahifasi yoki tafsilot ochiq tursa orqadagi asosiy sahifa aylanmaydi.
// Ular ko'p joyda ochilib-yopiladi — har birida qo'lda qulflamaslik uchun class o'zgarishini kuzatamiz
const SCROLL_LOCK_LAYERS = '.modal-backdrop, #txPageOverlay, #txDetailBackdrop';

function syncScrollLock() {
  const anyOpen = !!document.querySelector('.modal-backdrop.active, #txPageOverlay.open, #txDetailBackdrop.active');
  document.documentElement.classList.toggle('scroll-locked', anyOpen);
}

const _scrollLockObserver = new MutationObserver(syncScrollLock);
document.querySelectorAll(SCROLL_LOCK_LAYERS).forEach(el =>
  _scrollLockObserver.observe(el, { attributes: true, attributeFilter: ['class'] })
);

// ==========================================
// CUSTOM SELECT — native <select> ni to'liq stillangan
// (tema ranglariga mos) dropdown bilan almashtiradi.
// ==========================================

function enhanceCustomSelect(select) {
  if (select.dataset.csEnhanced) return;
  select.dataset.csEnhanced = '1';

  const wrapper = document.createElement('div');
  wrapper.className = 'custom-select-wrapper';
  select.parentNode.insertBefore(wrapper, select);
  wrapper.appendChild(select);

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'custom-select-trigger';
  trigger.innerHTML = '<span></span>';
  wrapper.appendChild(trigger);

  const panel = document.createElement('div');
  panel.className = 'custom-select-panel';
  document.body.appendChild(panel);

  const labelSpan = trigger.querySelector('span');

  function labelHtml(opt) {
    if (!opt) return '';
    const plus = opt.value === '__custom__' ? icon('plus') + ' ' : '';
    return plus + escapeHtml(opt.textContent);
  }

  function sync() {
    const opt = select.options[select.selectedIndex];
    labelSpan.innerHTML = labelHtml(opt);
    trigger.classList.toggle('placeholder', !select.value);
    trigger.classList.toggle('disabled', select.disabled);
  }

  function buildPanel() {
    panel.innerHTML = '';
    Array.from(select.options).forEach((opt) => {
      const item = document.createElement('div');
      item.className = 'custom-select-option';
      item.innerHTML = labelHtml(opt);
      if (opt.disabled) {
        item.classList.add('disabled');
      } else {
        if (opt.value === select.value) item.classList.add('selected');
        item.addEventListener('click', () => {
          select.value = opt.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
          sync();
          close();
        });
      }
      panel.appendChild(item);
    });
  }

  function position() {
    const r = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - r.bottom - 12;
    panel.style.left = r.left + 'px';
    panel.style.width = r.width + 'px';
    panel.style.maxHeight = Math.max(120, Math.min(260, spaceBelow)) + 'px';
    panel.style.top = (r.bottom + 6) + 'px';
  }

  function open() {
    if (select.disabled) return;
    document.querySelectorAll('.custom-select-panel.open').forEach(p => {
      if (p !== panel) p.classList.remove('open');
    });
    buildPanel();
    kbIndex = -1;
    position();
    panel.classList.add('open');
    wrapper.classList.add('open');
  }

  function close() {
    panel.classList.remove('open');
    wrapper.classList.remove('open');
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.classList.contains('open') ? close() : open();
  });

  // Klaviatura: yopiq vaqtda ↑/↓ qiymatni almashtiradi (native select kabi), ochiq vaqtda ro'yxat bo'ylab yuradi, Enter tanlaydi
  // (Esc umumiy ishlovchida; Space tugmaning o'z bosilishi bilan ochadi/yopadi)
  let kbIndex = -1;
  const enabledOptions = () => Array.from(select.options).filter(o => !o.disabled);
  const kbHighlight = (i) => {
    const items = Array.from(panel.querySelectorAll('.custom-select-option:not(.disabled)'));
    if (!items.length) return;
    kbIndex = (i + items.length) % items.length;
    items.forEach((it, j) => { it.style.background = j === kbIndex ? 'var(--bg-sunken)' : ''; });
    items[kbIndex].scrollIntoView({ block: 'nearest' });
  };
  trigger.addEventListener('keydown', (e) => {
    const down = e.key === 'ArrowDown', up = e.key === 'ArrowUp';
    const isOpen = panel.classList.contains('open');
    if (e.key === 'Enter' && isOpen && kbIndex >= 0) {
      e.preventDefault();
      panel.querySelectorAll('.custom-select-option:not(.disabled)')[kbIndex]?.click();
    } else if ((down || up) && isOpen) {
      e.preventDefault();
      kbHighlight(kbIndex + (down ? 1 : -1));
    } else if ((down || up) && !select.disabled) {
      e.preventDefault();
      const opts = enabledOptions();
      const i = opts.findIndex(o => o.value === select.value) + (down ? 1 : -1);
      if (i < 0 || i >= opts.length) return;
      select.value = opts[i].value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
      sync();
    }
  });

  window.addEventListener('scroll', () => {
    if (panel.classList.contains('open')) position();
  }, true);
  window.addEventListener('resize', () => {
    if (panel.classList.contains('open')) close();
  });

  // select.innerHTML qayta to'ldirilganda (API dan kategoriya/hamyon kelganda)
  // trigger'dagi matnni avtomatik yangilaydi.
  new MutationObserver(sync).observe(select, { childList: true });

  select._csSync = sync;
  sync();
}

function enhanceAllSelects(root = document) {
  root.querySelectorAll('select.form-control').forEach(enhanceCustomSelect);
}

document.addEventListener('click', () => {
  document.querySelectorAll('.custom-select-panel.open').forEach(p => p.classList.remove('open'));
  document.querySelectorAll('.custom-select-wrapper.open').forEach(w => w.classList.remove('open'));
});

// form.reset() select'ning value'sini DOM mutatsiyasiz o'zgartiradi —
// shu sabab trigger matnini qo'lda qayta sinxronlaymiz.
const _nativeFormReset = HTMLFormElement.prototype.reset;
HTMLFormElement.prototype.reset = function () {
  _nativeFormReset.call(this);
  this.querySelectorAll('select.form-control').forEach(s => s._csSync && s._csSync());
};

enhanceAllSelects();

// ==========================================
// DATA FETCHING
// ==========================================

async function fetchSummary() {
  try {
    const res = await fetch(`${API_BASE}/wallets/summary/`);
    if (res.ok) {
      state.summary = await res.json();
      renderSummary();
    }
  } catch (err) {
    console.error('Error fetching summary:', err);
  }
}

async function fetchWallets() {
  try {
    const res = await fetch(`${API_BASE}/wallets/`);
    if (res.ok) {
      const data = await res.json();
      state.wallets = data.results || data;
      renderWallets();
      populateWalletDropdowns();
    }
  } catch (err) {
    console.error('Error fetching wallets:', err);
  }
}

async function fetchMembers() {
  try {
    const res = await fetch(`${API_BASE}/members/`);
    if (res.ok) {
      const data = await res.json();
      state.members = data.results || data;
      renderMembers();
      populateExpenseMemberDropdown();
    }
  } catch (err) {
    console.error('Error fetching members:', err);
  }
}

async function fetchCategories() {
  try {
    const [incRes, expRes] = await Promise.all([
      fetch(`${API_BASE}/categories/`),
      fetch(`${API_BASE}/expense-categories/`)
    ]);
    if (incRes.ok) {
      const d = await incRes.json();
      state.incomeCategories = d.results || d;
      populateIncomeCategoryDropdown();
    }
    if (expRes.ok) {
      const d = await expRes.json();
      state.expenseCategories = d.results || d;
      populateExpenseCategoryDropdown();
    }
  } catch (err) {
    console.error('Error fetching categories:', err);
  }
}

// Bosh sahifadagi "So'nggi operatsiyalar" uchun har turdan oxirgilari (to'liq ro'yxat — bo'lim sahifasida, oy bo'yicha)
async function fetchTransactions() {
  try {
    const limit = state.txLimit;
    const [expRes, incRes, trRes] = await Promise.all([
      fetch(`${API_BASE}/expenses/?limit=${limit}`),
      fetch(`${API_BASE}/incomes/?limit=${limit}`),
      fetch(`${API_BASE}/transfers/?limit=${limit}`)
    ]);

    if (expRes.ok) {
      const d = await expRes.json();
      state.expenses = d.results || d;
    }
    if (incRes.ok) {
      const d = await incRes.json();
      state.incomes = d.results || d;
    }
    if (trRes.ok) {
      const d = await trRes.json();
      state.transfers = d.results || d;
    }

    renderTransactions();
  } catch (err) {
    console.error('Error fetching transactions:', err);
  }
}

async function fetchDebts() {
  try {
    // Hammasi kerak: qarzlar tarixi va statistikasi barcha qarzlardan hisoblanadi (API 10 tadan sahifalaydi)
    state.debts = await _fetchAllPages(`${API_BASE}/debts/`);
    renderDebts();
    // Qarzlar tarixi sahifasi ochiq bo'lsa, u ham yangilansin
    if (document.getElementById('statsDebtsSection')?.style.display === '') renderDebtsPage();
  } catch (err) {
    console.error('Error fetching debts:', err);
  }
}

async function refreshAll() {
  await Promise.all([
    fetchSummary(),
    fetchWallets(),
    fetchMembers(),
    fetchCategories(),
    fetchTransactions(),
    fetchDebts(),
    fetchRecurring(),
    fetchGoals()
  ]);
  const pageOpen = document.getElementById('txPageOverlay').classList.contains('open');
  if (pageOpen && _walletPageId) {
    await loadWalletPageData();
  } else if (pageOpen && (_txPageMode === 'transactions' || _txPageMode === 'stats')) {
    // Operatsiya qo'shilgan yoki o'chirilgan bo'lsa ochiq oy ro'yxati / statistikasi ham yangilansin
    await _loadMonthlyStats({ silent: true });
  }
}

// ==========================================
// RENDERING FUNCTIONS
// ==========================================

// "1 234 567" yoki sent bo'lsa "1 234 567.50". 'uz-UZ' brauzerga qarab "1,234.5" yoki "1 234,5" beradi —
// vergulni bo'sh joyga almashtirish ikkinchisida kasrni buzardi, shuning uchun en-US asosida yasaymiz
const _moneyFormat = {
  whole: new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }),
  cents: new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
};
function formatNumber(amount) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return '0';
  const hasCents = Math.round(Math.abs(n) * 100) % 100 !== 0;
  return (hasCents ? _moneyFormat.cents : _moneyFormat.whole).format(n).replace(/,/g, ' ');
}

// Katta balans soni kartochkaga sig'masa shrift kichrayadi — telefonda "124 645 / 688" bo'lib ikki qatorga bo'linmasin.
// CSS sonning uzunligini bilmaydi, shuning uchun o'lchab moslaymiz (valyuta yozuvi rem'da — 2-3 marta yaqinlashtiriladi)
function fitHeroBalance() {
  const el = document.getElementById('heroBalanceSum');
  if (!el) return;
  el.style.fontSize = '';
  for (let i = 0; i < 3 && el.clientWidth && el.scrollWidth > el.clientWidth; i++) {
    const size = parseFloat(getComputedStyle(el).fontSize);
    el.style.fontSize = Math.max(18, Math.floor(size * el.clientWidth / el.scrollWidth)) + 'px';
  }
}
// Eni o'zgarganda (ekran burilishi, oyna kattalashishi) qaytadan moslanadi; shrift eni o'zgartirmaydi — sikl bo'lmaydi
const _heroSumEl = document.getElementById('heroBalanceSum');
if (_heroSumEl && 'ResizeObserver' in window) new ResizeObserver(fitHeroBalance).observe(_heroSumEl);
else window.addEventListener('resize', fitHeroBalance);

function renderSummary() {
  const s = state.summary || {};
  // Balans valyuta bo'yicha: birinchisi katta, qolganlari uning tagida
  const balances = s.balances_by_currency || [];
  const main = balances[0] || { currency: 'UZS', total: 0 };
  const totalBalanceEl = document.getElementById('statTotalBalance');
  if (totalBalanceEl) totalBalanceEl.textContent = formatNumber(main.total);
  const totalCurrencyEl = document.getElementById('statTotalCurrency');
  if (totalCurrencyEl) totalCurrencyEl.textContent = main.currency;
  fitHeroBalance();
  renderBalanceExtra();

  const incEl = document.getElementById('statMonthlyIncome');
  if (incEl) incEl.textContent = formatNumber(s.monthly_income || 0);

  const expEl = document.getElementById('statMonthlyExpense');
  if (expEl) expEl.textContent = formatNumber(s.monthly_expense || 0);

  renderWeeklyExpenseChart(s.weekly_expenses || []);
  warnMissingRates(s.missing_rates);
}

// ==========================================
// XABARLAR (navbar qo'ng'irog'i)
// ==========================================
// Muhim ogohlantirishlar: muddati o'tgan yoki yaqinlashgan qarzlar va takroriy to'lovlar — ular ro'yxatlardan
// jonli hisoblanadi, qarz to'langach o'zi yo'qoladi. Eng tepada admin yuborgan xabarlar (state.notices, serverdan).

function _debtDaysLeft(d) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.round((new Date(d.due_date + 'T00:00:00') - today) / 86400000);
}

function getDebtAlerts() {
  return (state.debts || [])
    .filter(d => !d.is_settled && d.due_date)
    .map(d => ({ d, urgency: _debtUrgency(d), days: _debtDaysLeft(d) }))
    .filter(x => x.urgency === 'overdue' || x.urgency === 'soon')
    .sort((a, b) => a.days - b.days);
}

function renderNotifications() {
  const badge = document.getElementById('notifBadge');
  const list = document.getElementById('notifList');
  if (!badge || !list) return;

  const alerts = getDebtAlerts();
  const recurringAlerts = getRecurringAlerts();
  const supportUnread = state.supportUnread || 0;
  const notices = state.notices || [];
  const noticesUnread = state.noticesUnread || 0;
  const total = alerts.length + recurringAlerts.length + (supportUnread ? 1 : 0) + noticesUnread;

  if (total === 0) {
    badge.style.display = 'none';
  } else {
    badge.textContent = total > 99 ? '99+' : total;
    badge.style.display = '';
    const urgent = alerts.some(a => a.urgency === 'overdue') || recurringAlerts.some(a => a.r.last_error);
    badge.style.background = urgent ? 'var(--rose)' : 'var(--amber)';
  }

  // Takroriy to'lovlar: yozilmay qolgani (sababi bilan) va yaqinlashgani
  const recurringHtml = recurringAlerts.map(({ r, days }) => {
    const amount = `${formatNumber(r.summa)} ${escapeHtml(r.wallet_currency)}`;
    const text = r.last_error
      ? `<b>${escapeHtml(r.name)}</b> - avtomatik yozilmadi`
      : `<b>${escapeHtml(r.name)}</b> - ${days === 0 ? 'bugun' : days === 1 ? 'ertaga' : `${days} kundan keyin`} ${r.kind === 'income' ? 'tushadi' : "to'lanadi"}`;
    return `
      <button type="button" class="notif-item clickable" data-notif-recurring="${r.id}">
        <span class="notif-dot ${r.last_error ? 'overdue' : 'soon'}"></span>
        <span class="notif-body">
          <div class="notif-text">${text}</div>
          <div class="notif-time">${r.last_error ? escapeHtml(r.last_error) : `${amount} · ${escapeHtml(r.wallet_name)}`}</div>
        </span>
      </button>`;
  }).join('');

  // Yordam: admin javob yozgan (bosilsa Sozlamalar → Yordam ochiladi)
  const supportHtml = supportUnread ? `
      <button type="button" class="notif-item clickable" data-notif-support="1">
        <span class="notif-dot soon"></span>
        <span class="notif-body">
          <div class="notif-text"><b>Admin javob berdi</b></div>
          <div class="notif-time">${supportUnread} ta yangi xabar · Yordam</div>
        </span>
      </button>` : '';

  // Admin xabarlari: alohida ko'rinishda (yashil fon, "Admin" belgisi), o'qilmagani nuqta bilan.
  // Matn admin yozgani — tarjima qilinmaydi (data-no-i18n)
  const noticesHtml = notices.map(n => `
      <div class="notif-item notif-admin${n.is_read ? '' : ' is-unread'}">
        <span class="notif-admin-icon">${icon('megaphone')}</span>
        <span class="notif-body">
          <div class="notif-admin-head"><span class="notif-admin-badge">Admin</span>${n.broadcast ? '<span class="notif-admin-scope">Hammaga</span>' : ''}${n.is_read ? '' : '<span class="notif-admin-new" aria-label="Yangi"></span>'}</div>
          <div class="notif-text notif-admin-text" data-no-i18n>${escapeHtml(n.text)}</div>
          <div class="notif-time">${escapeHtml(formatUzDate(n.created_at, { year: true, time: true }))}</div>
        </span>
      </div>`).join('');

  list.innerHTML = (total || notices.length) ? noticesHtml + supportHtml + recurringHtml + alerts.map(({ d, urgency, days }) => {
    const when = urgency === 'overdue'
      ? `muddati ${Math.abs(days)} kun oldin o'tgan (${formatDueDate(d)})`
      : (days === 0 ? 'muddati bugun tugaydi' : `muddatiga ${days} kun qoldi (${formatDueDate(d)})`);
    const kind = d.debt_type === 'give' ? 'Sizga qaytarishi kerak' : 'Siz qaytarishingiz kerak';
    return `
      <button type="button" class="notif-item clickable" data-notif-debt="1">
        <span class="notif-dot ${urgency}"></span>
        <span class="notif-body">
          <div class="notif-text"><b>${escapeHtml(d.person_name)}</b> - qarz ${when}</div>
          <div class="notif-time">${kind} · qoldiq ${formatNumber(d.remaining_summa)} ${debtCurrency(d)}</div>
        </span>
      </button>`;
  }).join('') : `<div class="notif-empty">Hozircha xabarlar yo'q</div>`;
}

function _setNotifPanel(open) {
  const panel = document.getElementById('notifPanel');
  const btn = document.getElementById('btnNotif');
  if (!panel || !btn) return;
  const wasOpen = !panel.hidden;
  panel.hidden = !open;
  btn.setAttribute('aria-expanded', String(open));
  if (open) {
    renderNotifications();
    markNoticesRead();
  } else if (wasOpen && (state.notices || []).some(n => !n.is_read && n.seen)) {
    // Ochiq turganda ko'rilganlar yopilgandan keyin oddiy (o'qilgan) ko'rinishga o'tadi
    state.notices.forEach(n => { if (n.seen) n.is_read = true; });
    renderNotifications();
  }
}

// ADMIN XABARLARI: admin panelidan yuboriladi (panel/notices/). Yangisi borligi Yordam bilan bir xil
// so'rovda bilinadi (support/unread/ → notices_unread), shunda ro'yxat qayta olinadi
async function fetchNotices() {
  try {
    const res = await fetch(`${API_BASE}/notices/`);
    if (!res.ok) return;
    const data = await res.json();
    state.notices = data.notices;
    state.noticesUnread = data.unread;
    renderNotifications();
    if (document.getElementById('notifPanel')?.hidden === false) markNoticesRead();
  } catch (e) { /* tarmoq uzilgan — keyingi so'rovda */ }
}

// Qo'ng'iroq ochilganda: badge darhol kamayadi, xabarlar esa panel yopilguncha "yangi" ko'rinishida qoladi
async function markNoticesRead() {
  const fresh = (state.notices || []).filter(n => !n.is_read && !n.seen);
  if (!fresh.length) return;
  fresh.forEach(n => { n.seen = true; });
  state.noticesUnread = 0;
  renderNotifications();
  try {
    await fetch(`${API_BASE}/notices/read/`, { method: 'POST' });
  } catch (e) { /* keyingi ochilishda qayta belgilanadi */ }
}

document.getElementById('btnNotif')?.addEventListener('click', (e) => {
  e.stopPropagation();
  _setNotifPanel(document.getElementById('notifPanel').hidden);
});
document.getElementById('notifList')?.addEventListener('click', (e) => {
  const recurringItem = e.target.closest('[data-notif-recurring]');
  if (recurringItem) {
    _setNotifPanel(false);
    openRecurringModal(Number(recurringItem.dataset.notifRecurring));
    return;
  }
  if (e.target.closest('[data-notif-support]')) {
    _setNotifPanel(false);
    openSettings();
    switchSettingsTab('support');
    return;
  }
  if (e.target.closest('[data-notif-debt]')) {
    _setNotifPanel(false);
    openDebtsPage();
  }
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('#notifWrap')) _setNotifPanel(false);
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || document.getElementById('notifPanel')?.hidden !== false) return;
  e.preventDefault(); // Esc faqat xabarlar panelini yopadi
  _setNotifPanel(false);
});

const WEEKDAY_FULL_NAMES = { Du: 'Dushanba', Se: 'Seshanba', Ch: 'Chorshanba', Pa: 'Payshanba', Ju: 'Juma', Sh: 'Shanba', Ya: 'Yakshanba' };

function renderWeeklyExpenseChart(weeklyData = []) {
  const container = document.getElementById('weeklyExpenseChart');
  if (!container) return;

  const total = weeklyData.reduce((sum, d) => sum + (d.expense || 0), 0);
  if (!weeklyData.length || total === 0) {
    container.innerHTML = `<div class="weekly-rank-empty">Ma'lumotlar mavjud emas</div>`;
    return;
  }

  const maxVal = Math.max(...weeklyData.map(d => d.expense), 1);
  const sorted = [...weeklyData].sort((a, b) => b.expense - a.expense);

  container.innerHTML = sorted.map(d => {
    // Ustun uzunligi so'mga o'girilgan qiymat bo'yicha, yozuv esa asl valyutada: "100 USD", "50 000 UZS"
    const pct = d.expense > 0 ? Math.max((d.expense / maxVal) * 100, 4) : 0;
    const valueLabel = d.parts && d.parts.length
      ? d.parts.map(p => amountWithCurrency(p.total, p.currency)).join(' + ')
      : (d.expense > 0 ? amountWithCurrency(d.expense, 'UZS') : '0');
    const fullName = WEEKDAY_FULL_NAMES[d.label] || d.label;
    const clickable = d.expense > 0;
    return `
      <div class="weekly-rank-row${d.is_max ? ' is-max' : ''}${clickable ? ' is-clickable' : ''}"${clickable ? ` data-action="openWeekdayTxFilter" data-stop data-args="${actionArgs(d.label, fullName)}"` : ''}>
        <span class="weekly-rank-day">${escapeHtml(fullName)}</span>
        <div class="weekly-rank-track"><div class="weekly-rank-fill" style="width: ${pct}%;"></div></div>
        <span class="weekly-rank-value" title="${escapeHtml(valueLabel)}">${escapeHtml(valueLabel)}</span>
      </div>
    `;
  }).join('');
}

// Umumiy balans tagida boshqa valyutalar: "va 200 USD Dollar hamyonida".
// Matn bo'laklari alohida tugunlarda — i18n.js ularni "va" va "{0} hamyonida" kalitlari bo'yicha tarjima qiladi
function renderBalanceExtra() {
  const extraEl = document.getElementById('heroBalanceExtra');
  if (!extraEl) return;
  const extra = (state.summary?.balances_by_currency || []).slice(1);
  if (!extra.length) { extraEl.innerHTML = ''; return; }
  const parts = extra.map(b => {
    const owners = state.wallets.filter(w => w.currency === b.currency);
    const where = owners.length === 1 ? `${escapeHtml(owners[0].name)} hamyonida`
      : owners.length > 1 ? `${owners.length} ta hamyonda` : '';
    return `<span class="hero-extra-item"><b class="hero-extra-amount">${formatNumber(b.total)} ${escapeHtml(b.currency)}</b>${where ? ` <span>${where}</span>` : ''}</span>`;
  });
  extraEl.innerHTML = `<span>va</span> ${parts.join('<span class="hero-extra-sep">·</span>')}`;
}

// "Umumiy balans" kartochkasi ichida har bir hamyonning balansi
function renderHeroWallets() {
  const box = document.getElementById('heroWalletList');
  if (!box) return;
  // Hamyon bitta bo'lsa umumiy balans bilan bir xil bo'ladi: ko'rsatilmaydi
  if (state.wallets.length < 2) { box.innerHTML = ''; return; }
  box.innerHTML = state.wallets.map(w => `
    <button type="button" class="hero-wallet-cell" data-wallet-id="${w.id}" title="${escapeHtml(w.name)}: amallarni ko'rish">
      <span class="hero-wallet-name">${icon('card')}<span>${escapeHtml(w.name)}</span></span>
      <span class="hero-wallet-amount">${formatNumber(w.summa)} <small>${escapeHtml(w.currency)}</small></span>
    </button>`).join('');
  // Boshqa valyutadagi balans tagidagi "... hamyonida" yozuvi hamyonlar ro'yxatiga bog'liq
  renderBalanceExtra();
}

// Bosh sahifadagi "Hamyonlar" kartochkasida nechta hamyon ko'rinadi; qolganlari "Barcha hamyonlar" sahifasida
const HOME_WALLETS_LIMIT = 2;

function renderWallets() {
  renderHeroWallets();
  renderDebts(); // ko'rinadigan qarzlar soni = kartochkadagi hamyonlar soni
  renderAllWalletsPage();
  const container = document.getElementById('walletsList');
  if (!container) return;

  if (state.wallets.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Hamyon mavjud emas</p>`;
    return;
  }

  // Qolgan hamyonlar — sarlavha ("Hamyonlar ›") bosilganda ochiladigan sahifada
  container.innerHTML = state.wallets.slice(0, HOME_WALLETS_LIMIT).map(walletCardHtml).join('');
}

// "Barcha hamyonlar" sahifasi ochiq bo'lsa, hamyon qo'shilganda/o'chirilganda ro'yxat ham yangilanadi
function renderAllWalletsPage() {
  const list = document.getElementById('allWalletsList');
  if (!list || _txPageMode !== 'wallets') return;
  list.innerHTML = state.wallets.length ? state.wallets.map(walletCardHtml).join('')
    : `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Hamyon mavjud emas</p>`;
  document.getElementById('txPageMonth').textContent = `${state.wallets.length} ta hamyon`;
}

function walletCardHtml(w) {
  return `
    <div class="wallet-compact-card is-clickable" data-wallet-id="${w.id}" role="button" tabindex="0" title="${escapeHtml(w.name)}: amallarni ko'rish va tahrirlash">
      <div class="wallet-compact-info">
        <div class="wallet-compact-name" style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${icon(w.is_goal ? 'target' : 'card')} ${escapeHtml(w.name)}</div>
        <div style="font-size: 0.75rem; color: var(--text-subtle);">${w.is_goal ? '<span>Maqsad hamyoni</span> · ' : ''}${escapeHtml(w.currency)}</div>
      </div>
      <div class="wallet-compact-side" style="display: flex; align-items: center; gap: 10px;">
        <div style="font-weight: 600; font-size: 1.05rem; color: var(--text-main);">
          ${formatNumber(w.summa)} <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(w.currency)}</span>
        </div>
        ${!w.is_goal && state.wallets.filter((x) => !x.is_goal).length > 1 ? `
          <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="Hamyonni o'chirish" data-action="deleteWallet" data-stop data-args="${actionArgs(w.id)}">${icon('trash')}</button>
        ` : ''}
      </div>
    </div>`;
}

// Bosh sahifadagi Doimiy to'lovlar / Maqsadlar / A'zolar kartochkasida ro'yxatdan faqat 1 ta yozuv ko'rsatiladi
// (kartochka bosilsa butun ro'yxat sahifasi ochiladi). Ma'lumot bo'lmasa kartochka faqat sarlavha bo'lib qoladi
function renderHomePreview(id, html) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = html || '';
  el.closest('.card-header-only')?.classList.toggle('has-preview', !!html);
}

function renderMembers() {
  updateHomeListCount();
  const first = state.members[0];
  renderHomePreview('membersPreview', first
    ? `<div class="member-compact-card"><div style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${memberIcon(first.kind)} ${escapeHtml(first.name)}</div></div>`
    : '');
  const container = document.getElementById('membersList');
  if (!container) return;

  if (state.members.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">A'zo qo'shilmagan — xarajat qilganda "Kimga?" savoli ko'rinmaydi</p>`;
    return;
  }

  container.innerHTML = state.members.map(m => `
    <div class="member-compact-card is-clickable" data-member-id="${m.id}" data-member-name="${escapeHtml(m.name)}" title="${escapeHtml(m.name)}ga sarflangan xarajatlarni ko'rish">
      <div style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${memberIcon(m.kind)} ${escapeHtml(m.name)}</div>
      <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="A'zoni o'chirish" data-action="deleteMember" data-stop data-args="${actionArgs(m.id)}">${icon('trash')}</button>
    </div>
  `).join('');
}

// A'zo turi bo'yicha icon: bitta odam yoki butun oila
function memberIcon(kind) {
  return icon(kind === 'family' ? 'members' : 'person');
}

function populateExpenseMemberDropdown() {
  const el = document.getElementById('expenseMemberSelect');
  if (!el) return;
  const currentVal = el.value;
  const toOption = m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`;
  const people = state.members.filter(m => m.kind !== 'family');
  const families = state.members.filter(m => m.kind === 'family');
  const options = ['<option value="">-- O\'zim uchun --</option>'];
  if (people.length && families.length) {
    options.push(`<optgroup label="Odamlar">${people.map(toOption).join('')}</optgroup>`);
    options.push(`<optgroup label="Oilalar">${families.map(toOption).join('')}</optgroup>`);
  } else {
    options.push(...state.members.map(toOption));
  }
  el.innerHTML = options.join('');
  if (currentVal && Array.from(el.options).some(o => o.value === currentVal)) {
    el.value = currentVal;
  }

  const group = document.getElementById('expenseMemberGroup');
  if (group) group.style.display = state.members.length > 0 ? '' : 'none';
}

// Raw item lookup for detail drawer
const _txDetailMap = {};

// Build sorted list from state (yoki "Barcha operatsiyalar" sahifasida — tanlangan oy operatsiyalaridan)
function _buildTxList(filter = 'all', source = state) {
  let list = [];

  if (filter === 'all' || filter === 'expenses') {
    source.expenses.forEach(e => {
      const key = `expense_${e.id}`;
      _txDetailMap[key] = e;
      list.push({ type: 'expense', key, id: e.id, title: e.category_name || 'Chiqim', amount: e.summa, currency: e.wallet_currency, wallet: e.wallet_name || 'Hamyon', date: e.date, icon: 'expenseArrow' });
    });
  }
  if (filter === 'all' || filter === 'incomes') {
    source.incomes.forEach(i => {
      const key = `income_${i.id}`;
      _txDetailMap[key] = i;
      list.push({ type: 'income', key, id: i.id, title: i.category_name || 'Kirim', amount: i.summa, currency: i.wallet_currency, wallet: i.wallet_name || 'Hamyon', date: i.date, icon: 'incomeArrow' });
    });
  }
  if (filter === 'all' || filter === 'transfers') {
    source.transfers.forEach(t => {
      const key = `transfer_${t.id}`;
      _txDetailMap[key] = t;
      list.push({ type: 'transfer', key, id: t.id, title: `O'tkazma`, amount: t.summa, currency: t.from_currency, amountText: transferAmountText(t), wallet: `${t.from_wallet_name} → ${t.to_wallet_name}`, date: t.date, icon: 'transfer' });
    });
  }
  list.sort((a, b) => new Date(b.date) - new Date(a.date));
  return list;
}

function _txItemHtml(item) {
  const sign = item.sign !== undefined ? item.sign : (item.type === 'income' ? '+' : item.type === 'transfer' ? '' : '-');
  const click = item.noDetail ? ' style="cursor:default;"' : ` data-action="openTxDetail" data-args="${actionArgs(item.key, item.type, item.id)}"`;
  return `
    <div class="tx-compact-item"${click}>
      <div class="tx-icon-badge ${item.type}">${icon(item.icon)}</div>
      <div class="tx-compact-body">
        <div class="tx-compact-name">${escapeHtml(item.title)}</div>
        <div class="tx-compact-sub">${formatDate(item.date)} · ${escapeHtml(item.wallet)}</div>
      </div>
      <div class="tx-compact-amount ${item.type}">${sign}${escapeHtml(item.amountText || amountWithCurrency(item.amount, item.currency))}</div>
    </div>`;
}

// ── Kun / A'zo bo'yicha filtrlangan operatsiyalar oynasi ──────────
function openWeekdayTxFilter(weekdayCode, weekdayFullName) {
  _loadTxFilterModal({
    title: `${weekdayFullName} kuni`,
    url: `${API_BASE}/expenses/?weekday=${weekdayCode}`,
    emptyText: `${weekdayFullName} kuni xarajat topilmadi`
  });
}

function openMemberTxFilter(memberId, memberName) {
  _loadTxFilterModal({
    title: memberName,
    url: `${API_BASE}/expenses/?member=${memberId}`,
    emptyText: `${memberName} uchun xarajat topilmadi`
  });
}

async function _loadTxFilterModal({ title, url, emptyText }) {
  const titleEl = document.getElementById('txFilterTitle');
  const summaryEl = document.getElementById('txFilterSummary');
  const listEl = document.getElementById('txFilterList');

  if (titleEl) titleEl.innerHTML = `<span>${icon('receipt')}</span> ${escapeHtml(title)}`;
  if (summaryEl) summaryEl.innerHTML = '';
  if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:20px 0;color:var(--text-subtle);font-size:0.85rem;">Yuklanmoqda...</div>`;
  openModal('modalTxFilter');

  let items = [];
  try {
    // Hamma sahifalar yig'iladi — faqat birinchi 200 tasi olinsa "Jami sarflangan" kam chiqardi
    items = await _fetchAllPages(url);
  } catch (e) {
    console.error('Tx filter fetch error:', e);
  }

  if (items.length === 0) {
    if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:20px 0;color:var(--text-subtle);font-size:0.85rem;">${escapeHtml(emptyText)}</div>`;
    return;
  }

  // Har xil valyutadagi harajatlar alohida ko'rsatiladi: "250 000 UZS + 30 USD"
  const totals = sumByCurrency(items, e => e.summa, e => e.wallet_currency);
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="tx-filter-total-label">Jami sarflangan</div>
      <div class="tx-filter-total-value">${formatCurrencyTotals(totals)}</div>
    `;
  }

  const txItems = items
    .map(e => {
      const key = `expense_${e.id}`;
      _txDetailMap[key] = e;
      return { type: 'expense', key, id: e.id, title: e.category_name || 'Chiqim', amount: e.summa, currency: e.wallet_currency, wallet: e.wallet_name || 'Hamyon', date: e.date, icon: 'expenseArrow' };
    })
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  if (listEl) listEl.innerHTML = txItems.map(_txItemHtml).join('');
}

document.addEventListener('click', e => {
  const card = e.target.closest('.member-compact-card');
  if (!card) return;
  openMemberTxFilter(Number(card.dataset.memberId), card.dataset.memberName);
});

// ── Dashboard preview: last 3 items ──────────────────────────
function renderTransactions() {
  const container = document.getElementById('txPreviewList');
  if (!container) return;

  // Populate detail map for all types (needed for drawer)
  _buildTxList('all');

  const list = _buildTxList('all').slice(0, 3);

  if (list.length === 0) {
    container.innerHTML = `<div style="text-align:center;padding:18px 0;color:var(--text-subtle);font-size:0.85rem;">Hozircha amallar yo'q</div>`;
    return;
  }
  container.innerHTML = list.map(_txItemHtml).join('');
}


// ==========================================
// OYLIK STATISTIKA SAHIFASI
// ==========================================

// Joriy ko'rinayotgan davr: oy/yil yoki ixtiyoriy oraliq (_statsRange bo'lsa oy/yil e'tiborsiz qoladi)
let _statsYear  = new Date().getFullYear();
let _statsMonth = new Date().getMonth() + 1;  // 1-indexed
let _statsRange = null;  // { from: 'YYYY-MM-DD', to: 'YYYY-MM-DD' } — ikkala kun ham kiradi
let _txPageFilter = 'all';
let _statsData = null;  // oxirgi kelgan stats
// Ochiq bo'lim sahifasi: 'stats' | 'transactions' | 'debts' | 'wallet'
let _txPageMode = 'transactions';
// "Barcha operatsiyalar" sahifasi: tanlangan oyning hamma operatsiyalari ({ expenses, incomes, transfers } yoki { error })
let _monthOps = null;
let _monthLoadSeq = 0;

// Navbar bo'limlari uchun sarlavhalar
const TX_FILTER_TITLES = {
  all: 'Barcha amallar',
  incomes: 'Barcha kirimlar',
  expenses: 'Barcha chiqimlar',
  transfers: "Barcha o'tkazmalar",
};

// Navbarda ochiq bo'lim (Moliya / Kirim / Chiqim / Qarz / Kurs) belgilanadi. null — bosh sahifa va undan ochiladigan
// sahifalar (statistika, hamyon) "Moliya" ostida; mos bo'limi yo'q filtrda ("Barchasi") hech biri belgilanmaydi
function setNavActive(section) {
  const current = section || 'home';
  document.querySelectorAll('#navSections .nav-section-link').forEach(link => {
    const on = link.dataset.navSection === current;
    link.classList.toggle('is-active', on);
    if (on) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
}

// Bo'lim sahifasida (txPageOverlay) bir vaqtda faqat bitta bo'lim ko'rinadi
const TX_PAGE_SECTIONS = ['statsOverviewSection', 'statsOperationsSection', 'statsDebtsSection', 'statsWalletSection',
  'statsRatesSection', 'statsWalletsSection', 'statsHomeListSection'];
function _showTxPageSection(id) {
  TX_PAGE_SECTIONS.forEach(s => { document.getElementById(s).style.display = s === id ? '' : 'none'; });
}

function openTxPage(mode = 'transactions', filter = 'all') {
  _txPageFilter = filter;
  resetListPage('tx');
  _statsYear  = new Date().getFullYear();
  _statsMonth = new Date().getMonth() + 1;
  _statsRange = null;

  // Tab holati tanlangan filtrga moslanadi
  document.querySelectorAll('#txPageTabs .tx-page-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.filter === filter)
  );

  const isStats = mode === 'stats';
  _txPageMode = isStats ? 'stats' : 'transactions';
  setNavActive(isStats ? null : filter);
  _showTxPageSection(isStats ? 'statsOverviewSection' : 'statsOperationsSection');
  _walletPageId = null;
  _setTxPageMonthNav(true);
  document.getElementById('txPageTitleText').textContent = isStats ? 'Oylik hisobot' : (TX_FILTER_TITLES[filter] || TX_FILTER_TITLES.all);
  document.getElementById('txPageTitleIcon').innerHTML = icon(isStats ? 'chart' : 'receipt');

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
  _loadMonthlyStats();
}

// ── Qarzlar tarixi sahifasi (to'langan + to'lanmagan) ──────────
let _debtPageFilter = 'all';

function openDebtsPage() {
  _debtPageFilter = 'all';
  resetListPage('debts');
  _txPageMode = 'debts';
  setNavActive('debts');
  document.querySelectorAll('#debtPageTabs .tx-page-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.debtFilter === 'all')
  );

  _showTxPageSection('statsDebtsSection');
  _walletPageId = null;
  _setTxPageMonthNav(false);
  document.getElementById('txPageTitleText').textContent = 'Qarzlar Tarixi';
  document.getElementById('txPageTitleIcon').innerHTML = icon('ledger');
  document.getElementById('txPageMonth').textContent = 'Barcha davr';

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
  renderDebtsPage();
}

// ── Takroriy to'lovlar / Maqsadlarim / A'zolarim sahifasi ──────────
// Bosh sahifada bu bo'limlar faqat sarlavha (kartochka bosilsa shu sahifa ochiladi). Ro'yxat konteynerlari
// (#recurringList, #goalsList, #membersList) sahifa ichida turadi — render va bosish logikasi o'zgarmagan
const HOME_LIST_PAGES = {
  recurring: { title: "Doimiy to'lovlar", icon: 'repeat', items: () => state.recurring },
  goals:     { title: 'Maqsadlar',        icon: 'target', items: () => state.goals },
  members:   { title: "A'zolar",          icon: 'members', items: () => state.members },
};
let _homeListKind = null;

function openHomeListPage(kind) {
  const page = HOME_LIST_PAGES[kind];
  if (!page) return;
  _homeListKind = kind;
  _txPageMode = 'homeList';
  setNavActive(null);
  _showTxPageSection('statsHomeListSection');
  document.querySelectorAll('#statsHomeListSection [data-home-list]').forEach(el => {
    el.style.display = el.dataset.homeList === kind ? '' : 'none';
  });
  _walletPageId = null;
  _setTxPageMonthNav(false);
  document.getElementById('txPageTitleText').textContent = page.title;
  document.getElementById('txPageTitleIcon').innerHTML = icon(page.icon);
  updateHomeListCount();

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
}

// Sarlavha ostidagi "3 ta" — yozuv qo'shilganda/o'chirilganda ham yangilanadi
function updateHomeListCount() {
  if (_txPageMode !== 'homeList' || !_homeListKind) return;
  document.getElementById('txPageMonth').textContent = `${(HOME_LIST_PAGES[_homeListKind].items() || []).length} ta`;
}

// Faqat sarlavhali kartochkalar (Takroriy to'lovlar, Maqsadlarim, A'zolarim) va Hamyonlar kartochkasi klaviaturada ham ochiladi
document.addEventListener('keydown', (e) => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches?.('.card-header-only, #walletsCard')) {
    e.preventDefault();
    e.target.click();
  }
});

// ── Barcha hamyonlar sahifasi: bosh sahifadagi kartochkada faqat HOME_WALLETS_LIMIT tasi ko'rinadi ──────────
function openWalletsPage() {
  _txPageMode = 'wallets';
  setNavActive(null);
  _showTxPageSection('statsWalletsSection');
  _walletPageId = null;
  _setTxPageMonthNav(false);
  document.getElementById('txPageTitleText').textContent = 'Hamyonlar';
  document.getElementById('txPageTitleIcon').innerHTML = icon('wallet');

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
  renderAllWalletsPage();
}

// ── Kurs sahifasi: Markaziy bankning bugungi kurslari (server keshlaydi: /rates/) ──────────
// Asosiy juftliklar kartochkada; kesishgan kurs (EUR → USD) ikki so'm kursidan hisoblanadi
const RATES_MAIN_PAIRS = [['USD', 'UZS'], ['EUR', 'UZS'], ['RUB', 'UZS'], ['GBP', 'UZS'], ['EUR', 'USD'], ['USD', 'RUB']];
// Ro'yxatda birinchi turadigan valyutalar (qolganlari alifbo tartibida keyingi sahifalarda)
const RATES_FEATURED = ['USD', 'EUR', 'RUB', 'KZT', 'GBP', 'CNY', 'TRY', 'AED', 'KRW', 'JPY', 'CHF'];
let _ratesData = null;      // { date, updatedAt, map: { USD: { rate, diff } } }
let _ratesSeq = 0;

function openRatesPage() {
  _txPageMode = 'rates';
  resetListPage('rates');
  setNavActive('rates');
  _showTxPageSection('statsRatesSection');
  _walletPageId = null;
  _setTxPageMonthNav(false);
  document.getElementById('txPageTitleText').textContent = 'Valyuta kurslari';
  document.getElementById('txPageTitleIcon').innerHTML = icon('exchange');
  document.getElementById('txPageMonth').textContent = 'Markaziy bank kursi';

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
  if (_ratesData) renderRatesPage();
  loadRatesPage();
}

async function loadRatesPage() {
  const seq = ++_ratesSeq;
  const status = document.getElementById('ratesStatus');
  if (!_ratesData) {
    status.className = 'rates-status';
    status.textContent = 'Kurslar yuklanmoqda...';
  }
  try {
    const res = await fetch(`${API_BASE}/rates/`);
    const data = await res.json().catch(() => ({}));
    if (seq !== _ratesSeq) return;
    if (!res.ok) throw new Error(data.error || "Valyuta kurslarini olib bo'lmadi.");
    const map = { UZS: { rate: 1, diff: 0 } };
    (data.rates || []).forEach(r => {
      map[r.currency] = { rate: Number(r.rate), diff: r.diff === null ? null : Number(r.diff) };
    });
    _ratesData = { date: data.date, updatedAt: data.updated_at, map };
    status.className = 'rates-status';
    status.textContent = '';
    renderRatesPage();
  } catch (err) {
    if (seq !== _ratesSeq) return;
    status.className = 'rates-status is-error';
    status.innerHTML = `<span>${escapeHtml(err.message || "Valyuta kurslarini olib bo'lmadi.")}</span>
      <button type="button" class="btn btn-subtle" data-action="loadRatesPage">Qayta urinish</button>`;
  }
}

// Valyuta nomi: ilovadagi ro'yxatdan (i18n.js tarjima qiladi), bo'lmasa brauzerning Intl nomi
let _currencyDisplayNames = null;
function currencyName(code) {
  const opt = document.querySelector(`#currencyOptions option[value="${code}"]`);
  if (opt) return opt.textContent.trim();
  try {
    _currencyDisplayNames ||= new Intl.DisplayNames([window.i18n?.lang || 'uz', 'en'], { type: 'currency' });
    const name = _currencyDisplayNames.of(code);
    if (name && name !== code) return name;
  } catch (e) { /* eski brauzer — kodning o'zi */ }
  return code;
}

// Kurs kattaligiga qarab aniqlik: 12 345.67 / 1.0842 / 0.000083
function formatRateValue(n) {
  if (!Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  const digits = abs >= 100 ? 2 : abs >= 0.01 ? 4 : 6;
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, minimumFractionDigits: abs >= 100 ? 2 : 0 })
    .format(n).replace(/,/g, ' ');
}

// 1 from = ? to, va kechagi kursga nisbatan o'zgarish (Markaziy bank Diff bermagan bo'lsa null)
function ratePair(from, to) {
  const m = _ratesData?.map || {};
  const a = m[from], b = m[to];
  if (!a || !b) return null;
  const value = a.rate / b.rate;
  let change = null;
  if (a.diff !== null && b.diff !== null) {
    const prev = (a.rate - a.diff) / (b.rate - b.diff);
    if (prev > 0) change = { abs: value - prev, pct: (value - prev) / prev * 100 };
  }
  return { value, change };
}

function rateChangeHtml(change) {
  if (!change) return '<span class="rate-change"></span>';
  if (Math.abs(change.pct) < 0.005) return "<span class=\"rate-change is-flat\">O'zgarmadi</span>";
  const up = change.abs > 0;
  const sign = up ? '+' : '−';
  return `<span class="rate-change ${up ? 'is-up' : 'is-down'}" title="Kechagi kursga nisbatan">${icon(up ? 'up' : 'down')}<span>${sign}${formatRateValue(Math.abs(change.abs))}</span><span class="rate-change-pct">${sign}${Math.abs(change.pct).toFixed(2)}%</span></span>`;
}

// Markaziy bank sanasi "23.10.2026" ko'rinishida keladi
function _parseCbuDate(s) {
  const m = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(s || '');
  return m ? new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1])) : null;
}

// So'mdan boshqa valyutalar: avval mashhurlari, keyin qolganlari alifbo tartibida
function _ratesCodes() {
  const map = _ratesData.map;
  const featured = RATES_FEATURED.filter(c => map[c]);
  const rest = Object.keys(map).filter(c => c !== 'UZS' && !featured.includes(c)).sort();
  return [...featured, ...rest];
}

// "Boshqa valyutalar" jadvali — 10 tadan sahifalarga bo'linadi (LIST_PAGERS.rates)
function renderRatesTable() {
  if (!_ratesData) return;
  document.getElementById('ratesTable').innerHTML = pageSlice('rates', _ratesCodes()).map(code => {
    const p = ratePair(code, 'UZS');
    return `<div class="rates-row">
      <span class="rates-row-code">${code}</span>
      <span class="rates-row-name">${escapeHtml(currencyName(code))}</span>
      <span class="rates-row-value">${formatRateValue(p.value)}</span>
      ${rateChangeHtml(p.change)}
    </div>`;
  }).join('');
}

function renderRatesPage() {
  if (!_ratesData) return;
  const map = _ratesData.map;
  const rateDate = _parseCbuDate(_ratesData.date);
  if (rateDate) document.getElementById('txPageMonth').textContent = formatUzDate(rateDate, { year: true });

  document.getElementById('ratesMainGrid').innerHTML = RATES_MAIN_PAIRS.map(([from, to]) => {
    const p = ratePair(from, to);
    if (!p) return '';
    return `<div class="rate-card">
      <div class="rate-card-pair"><span class="rate-card-code">${from}</span><span class="rate-card-arrow">→</span><span>${to}</span></div>
      <div class="rate-card-value">${formatRateValue(p.value)}</div>
      <div class="rate-card-foot"><span class="rate-card-name">${escapeHtml(currencyName(from))}</span>${rateChangeHtml(p.change)}</div>
    </div>`;
  }).join('');

  renderRatesTable();

  // Kalkulyator ro'yxati: so'm, mashhur valyutalar, keyin qolganlari; tanlangan valyuta saqlanib qoladi
  const options = ['UZS', ..._ratesCodes()];
  ['ratesConvFrom', 'ratesConvTo'].forEach((id, i) => {
    const sel = document.getElementById(id);
    const keep = sel.value || (i === 0 ? 'USD' : 'UZS');
    sel.innerHTML = options.map(c => `<option value="${c}">${c} — ${escapeHtml(currencyName(c))}</option>`).join('');
    sel.value = map[keep] ? keep : options[i === 0 ? 1 : 0];
  });
  updateRatesConverter();

  const updated = _ratesData.updatedAt ? new Date(_ratesData.updatedAt) : null;
  const stale = updated && Date.now() - updated.getTime() > 24 * 3600 * 1000;
  document.getElementById('ratesSource').innerHTML =
    "<span>Manba: O'zbekiston Respublikasi Markaziy banki (cbu.uz)</span>" +
    (updated ? `<span${stale ? ' class="is-stale"' : ''}>${stale ? "Oxirgi saqlangan kurs" : 'Yangilangan'}: ${formatUzDate(updated, { year: true, time: true })}</span>` : '');
}

function updateRatesConverter() {
  const out = document.getElementById('ratesConvResult');
  if (!out || !_ratesData) return;
  const from = document.getElementById('ratesConvFrom').value;
  const to = document.getElementById('ratesConvTo').value;
  const amount = readAmount('ratesConvAmount');
  const p = ratePair(from, to);
  if (!p || !(amount > 0)) {
    out.innerHTML = '';
    return;
  }
  const result = amount * p.value;
  const resultText = result >= 1 ? formatNumber(Math.round(result * 100) / 100) : formatRateValue(result);
  out.innerHTML = `<div class="rates-conv-sum">${formatNumber(amount)} ${from} = <strong>${resultText} ${to}</strong></div>
    <div class="rates-conv-rate">${formatRateText(from, to, p.value)}</div>`;
}

document.getElementById('ratesConvAmount')?.addEventListener('input', updateRatesConverter);
document.getElementById('ratesConvFrom')?.addEventListener('change', updateRatesConverter);
document.getElementById('ratesConvTo')?.addEventListener('change', updateRatesConverter);
document.getElementById('ratesConvSwap')?.addEventListener('click', () => {
  const a = document.getElementById('ratesConvFrom'), b = document.getElementById('ratesConvTo');
  [a.value, b.value] = [b.value, a.value];
  [a, b].forEach(s => s._csSync?.());  // value DOM o'zgarishisiz almashadi — tugma matnini qo'lda yangilaymiz
  updateRatesConverter();
});

function renderDebtsPage() {
  renderDebtStatRow();
  renderDebtPageList();
}

function renderDebtStatRow() {
  const row = document.getElementById('debtStatRow');
  if (!row) return;

  const open = state.debts.filter(d => !d.is_settled);
  const remainingTotals = list => sumByCurrency(list, d => d.remaining_summa, d => d.currency);
  const toReceive = remainingTotals(open.filter(d => d.debt_type === 'give'));
  const toPay     = remainingTotals(open.filter(d => d.debt_type === 'take'));
  const settled   = state.debts.filter(d => d.is_settled).length;

  row.innerHTML = `
    <div class="debt-stat-box">
      <span class="debt-stat-label">Menga qaytarishadi</span>
      <span class="debt-stat-value" style="color:var(--emerald);">${formatCurrencyTotals(toReceive)}</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Men qaytaraman</span>
      <span class="debt-stat-value" style="color:var(--amber);">${formatCurrencyTotals(toPay)}</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Yopilgan qarzlar</span>
      <span class="debt-stat-value">${settled} ta</span>
    </div>
  `;
}

function renderDebtPageList() {
  const container = document.getElementById('debtPageList');
  if (!container) return;

  let list = state.debts;
  if (_debtPageFilter === 'open') list = list.filter(d => !d.is_settled);
  else if (_debtPageFilter === 'settled') list = list.filter(d => d.is_settled);

  if (list.length === 0) {
    clearListPager('debts');
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Bu filtr bo'yicha qarzlar yo'q</div>`;
    return;
  }

  // To'lanmaganlar shoshilinchligi bo'yicha, yopilganlar oxirida
  const sorted = [...list].sort((a, b) => {
    if (a.is_settled !== b.is_settled) return a.is_settled ? 1 : -1;
    return DEBT_URGENCY_RANK[_debtUrgency(a)] - DEBT_URGENCY_RANK[_debtUrgency(b)];
  });

  container.innerHTML = pageSlice('debts', sorted).map(d => {
    const isGive = d.debt_type === 'give';
    const typeLabel = isGive ? 'Qarz berdim' : 'Qarz oldim';
    const typeColor = isGive ? 'var(--emerald)' : 'var(--amber)';
    const paidPercent = d.summa > 0 ? Math.min(100, Math.round((d.paid_summa || 0) / d.summa * 100)) : 0;

    return `
      <div class="debt-history-row ${d.is_settled ? 'settled' : ''}">
        <div class="debt-history-main">
          <div class="debt-history-name">
            ${escapeHtml(d.person_name)}
            <span class="debt-history-type" style="color:${typeColor};">${typeLabel}</span>
            ${d.is_settled ? `<span class="debt-history-type" style="color:var(--emerald);">Yopilgan</span>` : ''}
          </div>
          <div class="debt-history-meta">
            ${formatNumber(d.paid_summa || 0)} / ${formatNumber(d.summa)} ${debtCurrency(d)} ${_debtDueBadge(d)}
          </div>
          <div class="stats-progress-track" style="margin-top:6px;">
            <div class="stats-progress-fill" style="width:${Math.max(2, paidPercent)}%;background:${d.is_settled ? 'var(--emerald)' : 'linear-gradient(90deg,#3b82f6,#60a5fa)'};"></div>
          </div>
        </div>
        <div class="debt-history-actions">
          ${!d.is_settled ? `
            <span class="debt-history-remaining">${formatNumber(d.remaining_summa)} ${debtCurrency(d)}</span>
            <button class="btn btn-subtle btn-xs" data-action="openRepayModal" data-args="${actionArgs(d.id)}">To'lash</button>
          ` : `<span style="font-size:0.75rem;color:var(--emerald);">${icon('check')}</span>`}
        </div>
      </div>
    `;
  }).join('');
}

// Qarzlar tarixi filtr tablari
document.getElementById('debtPageTabs')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.tx-page-tab');
  if (!btn) return;
  _debtPageFilter = btn.dataset.debtFilter;
  resetListPage('debts');
  document.querySelectorAll('#debtPageTabs .tx-page-tab').forEach(b => b.classList.toggle('active', b === btn));
  renderDebtPageList();
});

// ── Hamyon sahifasi: hamyon ma'lumotlari + shu hamyon bilan bog'liq operatsiyalar ──
function _setTxPageMonthNav(visible) {
  const nav = document.querySelector('#txPageOverlay .month-nav-controls');
  if (nav) nav.style.display = visible ? '' : 'none';
  _setPeriodPanel(false);
}

// Sahifalangan API'dan barcha yozuvlarni yuklaydi (har so'rovda 200 tadan)
async function _fetchAllPages(url) {
  const limit = 200;
  const out = [];
  for (let offset = 0; offset < 10000; offset += limit) {
    const res = await fetch(`${url}${url.includes('?') ? '&' : '?'}limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error(`So'rov muvaffaqiyatsiz: ${res.status}`);
    const data = await res.json();
    const items = Array.isArray(data) ? data : (data.results || []);
    out.push(...items);
    if (Array.isArray(data) || !data.next || items.length < limit) break;
  }
  return out;
}

function openWalletPage(walletId) {
  if (!state.wallets.find(w => w.id === walletId)) return;

  _walletPageId = walletId;
  _walletPageFilter = 'all';
  resetListPage('wallet');
  _walletPageData = null;
  _txPageMode = 'wallet';
  setNavActive(null);
  document.querySelectorAll('#walletPageTabs .tx-page-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.walletFilter === 'all')
  );

  _showTxPageSection('statsWalletSection');
  document.getElementById('txPageTitleIcon').innerHTML = icon('wallet');
  _setTxPageMonthNav(false);

  document.getElementById('txPageOverlay').classList.add('open');
  _rememberPageInHistory();
  renderWalletPage();
  loadWalletPageData();
}

async function loadWalletPageData() {
  const id = _walletPageId;
  if (!id) return;
  let data;
  try {
    const [incomes, expenses, transfersOut, transfersIn, debts] = await Promise.all([
      _fetchAllPages(`${API_BASE}/incomes/?wallet=${id}`),
      _fetchAllPages(`${API_BASE}/expenses/?wallet=${id}`),
      _fetchAllPages(`${API_BASE}/transfers/?from_wallet=${id}`),
      _fetchAllPages(`${API_BASE}/transfers/?to_wallet=${id}`),
      _fetchAllPages(`${API_BASE}/debts/?wallet=${id}`),
    ]);
    data = { incomes, expenses, transfersOut, transfersIn, debts };
  } catch (err) {
    console.error('Wallet page fetch error:', err);
    data = { error: true };
  }
  if (id !== _walletPageId) return; // foydalanuvchi boshqa sahifaga o'tib ketgan
  _walletPageData = data;
  renderWalletPage();
}

function _walletPageItems(filter) {
  const d = _walletPageData;
  if (!d || d.error) return [];
  const list = [];

  if (filter === 'all' || filter === 'incomes') {
    d.incomes.forEach(i => {
      const key = `income_${i.id}`;
      _txDetailMap[key] = i;
      list.push({ type: 'income', key, id: i.id, title: i.category_name || 'Kirim', amount: i.summa, currency: i.wallet_currency, wallet: i.wallet_name || 'Hamyon', date: i.date, icon: 'incomeArrow' });
    });
  }
  if (filter === 'all' || filter === 'expenses') {
    d.expenses.forEach(e => {
      const key = `expense_${e.id}`;
      _txDetailMap[key] = e;
      list.push({ type: 'expense', key, id: e.id, title: e.category_name || 'Chiqim', amount: e.summa, currency: e.wallet_currency, wallet: e.wallet_name || 'Hamyon', date: e.date, icon: 'expenseArrow' });
    });
  }
  if (filter === 'all' || filter === 'transfers') {
    const add = (t, outgoing) => {
      const key = `transfer_${t.id}`;
      _txDetailMap[key] = t;
      list.push({
        type: 'transfer', key, id: t.id,
        title: outgoing ? `O'tkazma → ${t.to_wallet_name}` : `O'tkazma ← ${t.from_wallet_name}`,
        // Kiruvchi o'tkazmada shu hamyonga tushgan summa (kurs bo'yicha) ko'rsatiladi
        amount: outgoing ? t.summa : (t.to_summa ?? t.summa), currency: outgoing ? t.from_currency : t.to_currency,
        wallet: outgoing ? t.from_wallet_name : t.to_wallet_name,
        date: t.date, icon: 'transfer', sign: outgoing ? '-' : '+'
      });
    };
    d.transfersOut.forEach(t => add(t, true));
    d.transfersIn.forEach(t => add(t, false));
  }
  if (filter === 'all' || filter === 'debts') {
    d.debts.forEach(x => {
      const give = x.debt_type === 'give';
      list.push({
        type: 'debt', key: `debt_${x.id}`, id: x.id, noDetail: true,
        title: `${give ? 'Qarz berdim' : 'Qarz oldim'}: ${x.person_name}`,
        amount: x.summa, currency: x.currency, wallet: x.wallet_name || 'Hamyon', date: x.created_at,
        icon: 'ledger', sign: give ? '-' : '+'
      });
    });
  }
  list.sort((a, b) => new Date(b.date) - new Date(a.date));
  return list;
}

function renderWalletPage() {
  const wallet = state.wallets.find(w => w.id === _walletPageId);
  if (!wallet) { closeTxPage(); return; } // hamyon o'chirilgan bo'lsa sahifa yopiladi

  const cur = escapeHtml(wallet.currency);
  document.getElementById('txPageTitleText').textContent = wallet.name;
  document.getElementById('txPageMonth').textContent = `Hamyon · ${wallet.currency}`;

  const created = formatUzDate(wallet.created_at, { year: true });
  document.getElementById('walletInfoCard').innerHTML = `
    <div class="wallet-info-main">
      <div class="wallet-info-icon">${icon(wallet.is_goal ? 'target' : 'wallet')}</div>
      <div>
        <div class="wallet-info-name">${escapeHtml(wallet.name)}</div>
        <div class="wallet-info-sub">${wallet.is_goal ? '<span>Maqsad hamyoni</span> · ' : ''}Valyuta: ${cur}${created ? ` · Yaratilgan: ${created}` : ''}</div>
      </div>
    </div>
    <div class="wallet-info-side">
      <div class="wallet-info-balance">
        <span class="debt-stat-label">Joriy qoldiq</span>
        <b>${formatNumber(wallet.summa)} ${cur}</b>
      </div>
      ${wallet.is_goal ? '' : `<button type="button" class="btn btn-subtle" data-action="openEditWallet">${icon('edit')} Tahrirlash</button>`}
    </div>`;

  const statRow = document.getElementById('walletStatRow');
  const listEl = document.getElementById('walletPageList');
  const d = _walletPageData;

  if (!d) {
    statRow.innerHTML = '';
    clearListPager('wallet');
    listEl.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Yuklanmoqda...</div>`;
    return;
  }
  if (d.error) {
    statRow.innerHTML = '';
    clearListPager('wallet');
    listEl.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">
      Amallarni yuklab bo'lmadi. <button type="button" class="btn btn-subtle btn-xs" data-action="loadWalletPageData">Qayta urinish</button></div>`;
    return;
  }

  const sum = arr => arr.reduce((acc, x) => acc + Number(x.summa || 0), 0);
  const count = d.incomes.length + d.expenses.length + d.transfersOut.length + d.transfersIn.length + d.debts.length;
  statRow.innerHTML = `
    <div class="debt-stat-box">
      <span class="debt-stat-label">Kirimlar</span>
      <span class="debt-stat-value" style="color:var(--emerald);">+${formatNumber(sum(d.incomes))} ${cur}</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Chiqimlar</span>
      <span class="debt-stat-value" style="color:var(--rose);">-${formatNumber(sum(d.expenses))} ${cur}</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Amallar soni</span>
      <span class="debt-stat-value">${count} ta</span>
    </div>`;

  const items = _walletPageItems(_walletPageFilter);
  if (!items.length) {
    clearListPager('wallet');
    const text = _walletPageFilter === 'all' ? "Bu hamyon bilan hali amallar yo'q" : "Bu bo'limda amallar yo'q";
    listEl.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">${text}</div>`;
    return;
  }
  listEl.innerHTML = pageSlice('wallet', items).map(_txItemHtml).join('');
}

function openEditWallet() {
  const wallet = state.wallets.find(w => w.id === _walletPageId);
  if (!wallet) return;
  document.getElementById('editWalletName').value = wallet.name;
  document.getElementById('editWalletCurrency').value = wallet.currency;
  document.getElementById('editWalletSumma').value = wallet.summa;
  openModal('modalEditWallet');
  document.getElementById('editWalletName').focus();
}

onSubmitOnce('formEditWallet', async (e) => {
  e.preventDefault();
  const id = _walletPageId;
  if (!id) return;
  const payload = {
    name: document.getElementById('editWalletName').value.trim(),
    currency: document.getElementById('editWalletCurrency').value.trim().toUpperCase(),
    summa: readAmount('editWalletSumma'),
  };

  try {
    const res = await fetch(`${API_BASE}/wallets/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast("Hamyon ma'lumotlari saqlandi");
      closeModal('modalEditWallet');
      await refreshAll();
    } else {
      showToast(extractErrorMessage(data, 'Hamyonni saqlashda xatolik'), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

document.getElementById('walletPageTabs')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.tx-page-tab');
  if (!btn) return;
  _walletPageFilter = btn.dataset.walletFilter;
  resetListPage('wallet');
  document.querySelectorAll('#walletPageTabs .tx-page-tab').forEach(b => b.classList.toggle('active', b === btn));
  renderWalletPage();
});

// Hamyon kartochkasini bosish (yoki Enter/Space) hamyon sahifasini ochadi
document.addEventListener('click', (e) => {
  const card = e.target.closest('.wallet-compact-card.is-clickable, .hero-wallet-cell');
  if (card) openWalletPage(Number(card.dataset.walletId));
});
document.addEventListener('keydown', (e) => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('.wallet-compact-card.is-clickable')) {
    e.preventDefault();
    openWalletPage(Number(e.target.dataset.walletId));
  }
});

// Telefondagi (va brauzerdagi) "orqaga" tugmasi bo'lim sahifasini yopadi: sahifa ochilganda tarixga bitta qadam
// qo'shiladi, yopilganda o'sha qadam qaytariladi. Ustida oyna yoki tafsilot ochiq bo'lsa, avval o'sha yopiladi
let _pageInHistory = false;

function _rememberPageInHistory() {
  if (_pageInHistory) return;
  history.pushState({ moliyaPage: true }, '');
  _pageInHistory = true;
}

window.addEventListener('popstate', () => {
  if (!_pageInHistory) return;
  if (document.getElementById('modalConfirm')?.classList.contains('active')) {
    _resolveConfirm(false);
  } else if (_activeDialogLayer()) {
    const modal = _topModal();
    if (modal) closeModal(modal.id); else closeTxDetail();
  } else {
    _pageInHistory = false;
    _hideTxPage();
    return;
  }
  history.pushState({ moliyaPage: true }, ''); // sahifa ochiq qoldi — uning qadami tarixga qaytariladi
});

function closeTxPage() {
  if (_pageInHistory) {
    history.back(); // popstate sahifani yopadi
    return;
  }
  _hideTxPage();
}

// Navbardagi "Moliya": ochiq bo'lim sahifasi yopiladi, bosh sahifa eng tepaga chiqadi va ma'lumotlar serverdan
// yangilanadi — pastga tortib yangilashdagi logotip kapsulasi aylanib turadi (_ptrRefresh)
function goHome() {
  if (document.getElementById('txPageOverlay')?.classList.contains('open')) closeTxPage();
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  _ptrRefresh();
}

function _hideTxPage() {
  _walletPageId = null;
  setNavActive(null);
  _setPeriodPanel(false);
  document.getElementById('txPageOverlay').classList.remove('open');
}

// ── Davr: oy yoki "dan — gacha" oralig'i ──────────────────────────
const _pad2 = n => String(n).padStart(2, '0');
// Mahalliy sana -> "YYYY-MM-DD" (toISOString UTC ga o'girib, Toshkentda yarim tundan keyin bir kun orqaga surardi)
function _isoDay(d) { return `${d.getFullYear()}-${_pad2(d.getMonth() + 1)}-${_pad2(d.getDate())}`; }
function _parseIsoDay(s) { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); }
function _addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
// Ikkala chekka kun ham kiradi; round — yozgi/qishki vaqt almashgan kunlarda sutka 23/25 soat bo'lishi uchun
function _daysInRange(from, to) { return Math.round((_parseIsoDay(to) - _parseIsoDay(from)) / 86400000) + 1; }
function _todayIso() { return _isoDay(new Date()); }
const PERIOD_MAX_DAYS = 366;  // server ham shundan uzun oraliqni rad etadi

// Tezkor tanlovlar: oy ({ year, month }) yoki oraliq ({ from, to }) qaytaradi
const PERIOD_PRESETS = {
  thisMonth: t => ({ year: t.getFullYear(), month: t.getMonth() + 1 }),
  lastMonth: t => { const d = new Date(t.getFullYear(), t.getMonth() - 1, 1); return { year: d.getFullYear(), month: d.getMonth() + 1 }; },
  last7:     t => ({ from: _isoDay(_addDays(t, -6)),  to: _isoDay(t) }),
  last30:    t => ({ from: _isoDay(_addDays(t, -29)), to: _isoDay(t) }),
  last90:    t => ({ from: _isoDay(_addDays(t, -89)), to: _isoDay(t) }),
  thisYear:  t => ({ from: `${t.getFullYear()}-01-01`, to: _isoDay(t) }),
};

function _setPeriod(p) {
  if (p.from) {
    _statsRange = { from: p.from, to: p.to };
  } else {
    _statsRange = null;
    _statsYear = p.year;
    _statsMonth = p.month;
  }
}

function _isCurrentPeriod(p) {
  return p.from
    ? !!_statsRange && _statsRange.from === p.from && _statsRange.to === p.to
    : !_statsRange && _statsYear === p.year && _statsMonth === p.month;
}

// Tanlangan davrning birinchi va oxirgi kuni (oy rejimida — oyning chegaralari)
function _periodBounds() {
  if (_statsRange) return _statsRange;
  const last = new Date(_statsYear, _statsMonth, 0).getDate();
  return { from: `${_statsYear}-${_pad2(_statsMonth)}-01`, to: `${_statsYear}-${_pad2(_statsMonth)}-${_pad2(last)}` };
}

function _periodQuery() {
  return _statsRange
    ? `date_from=${_statsRange.from}&date_to=${_statsRange.to}`
    : `year=${_statsYear}&month=${_statsMonth}`;
}

// "Oktabr 2026" | "5–20-okt, 2026" | "28-sen – 4-okt, 2026" | "15-dek, 2025 – 10-yan, 2026"
function _periodLabel() {
  if (!_statsRange) return `${UZ_MONTHS[_statsMonth - 1]} ${_statsYear}`;
  const a = _parseIsoDay(_statsRange.from), b = _parseIsoDay(_statsRange.to);
  if (_statsRange.from === _statsRange.to) return `${formatDate(a)}, ${a.getFullYear()}`;
  if (a.getFullYear() !== b.getFullYear()) return `${formatDate(a)}, ${a.getFullYear()} – ${formatDate(b)}, ${b.getFullYear()}`;
  if (a.getMonth() === b.getMonth()) return `${a.getDate()}–${formatDate(b)}, ${b.getFullYear()}`;
  return `${formatDate(a)} – ${formatDate(b)}, ${b.getFullYear()}`;
}

// Kelajakka o'tilmaydi: davr bugungi kunni (yoki joriy oyni) o'z ichiga olsa "keyingi" o'chiq
function _isPeriodAtPresent() {
  return _periodBounds().to >= _todayIso();
}

function _updatePeriodLabel() {
  const label = _periodLabel();
  const el = document.getElementById('monthNavLabel');
  if (el) el.textContent = label;
  const sub = document.getElementById('txPageMonth');
  if (sub) sub.textContent = label;
  const next = document.getElementById('btnNextMonth');
  if (next) next.disabled = _isPeriodAtPresent();
  if (_txPageMode === 'stats') {
    document.getElementById('txPageTitleText').textContent = _statsRange ? 'Hisobot' : 'Oylik hisobot';
  }
}

// ‹ › — oy rejimida bir oyga, oraliqda esa shu oraliq uzunligiga suradi ("Oxirgi 7 kun" -> undan oldingi 7 kun)
function _shiftPeriod(dir) {
  if (dir > 0 && _isPeriodAtPresent()) return;
  if (_statsRange) {
    const len = _daysInRange(_statsRange.from, _statsRange.to);
    _statsRange = {
      from: _isoDay(_addDays(_parseIsoDay(_statsRange.from), dir * len)),
      to:   _isoDay(_addDays(_parseIsoDay(_statsRange.to), dir * len)),
    };
  } else {
    const d = new Date(_statsYear, _statsMonth - 1 + dir, 1);
    _statsYear = d.getFullYear();
    _statsMonth = d.getMonth() + 1;
  }
  _onPeriodChanged();
}

function _onPeriodChanged() {
  _setPeriodPanel(false);
  resetListPage('tx');
  _loadMonthlyStats();
}

// Davr paneli: ochilganda maydonlar joriy davr bilan to'ldiriladi va mos tezkor tanlov belgilanadi
function _setPeriodPanel(open, { returnFocus = false } = {}) {
  const panel = document.getElementById('periodPanel');
  const btn = document.getElementById('btnPeriod');
  if (!panel || !btn || panel.hidden === !open) return;
  panel.hidden = !open;
  btn.setAttribute('aria-expanded', String(open));
  if (!open) {
    if (returnFocus) btn.focus();
    return;
  }
  const today = new Date();
  const todayIso = _isoDay(today);
  const { from, to } = _periodBounds();
  const fromEl = document.getElementById('periodFrom');
  const toEl = document.getElementById('periodTo');
  fromEl.max = toEl.max = todayIso;
  fromEl.value = from;
  toEl.value = to > todayIso ? todayIso : to;
  document.getElementById('periodRangeError').textContent = '';
  panel.querySelectorAll('[data-period-preset]').forEach(b => {
    b.setAttribute('aria-pressed', String(_isCurrentPeriod(PERIOD_PRESETS[b.dataset.periodPreset](today))));
  });
  (panel.querySelector('[aria-pressed="true"]') || panel.querySelector('[data-period-preset]')).focus();
}

document.getElementById('btnPeriod')?.addEventListener('click', () => {
  _setPeriodPanel(document.getElementById('periodPanel').hidden);
});
document.getElementById('periodPanel')?.addEventListener('click', (e) => {
  const preset = e.target.closest('[data-period-preset]');
  if (!preset) return;
  _setPeriod(PERIOD_PRESETS[preset.dataset.periodPreset](new Date()));
  _onPeriodChanged();
});
document.getElementById('formPeriodRange')?.addEventListener('submit', (e) => {
  e.preventDefault();
  const err = document.getElementById('periodRangeError');
  let from = document.getElementById('periodFrom').value;
  let to = document.getElementById('periodTo').value;
  if (!from || !to) { err.textContent = 'Ikkala sanani ham tanlang'; return; }
  if (from > to) [from, to] = [to, from]; // "YYYY-MM-DD" satrlari sana tartibida solishtiriladi
  if (to > _todayIso()) { err.textContent = "Kelajakdagi sanani tanlab bo'lmaydi"; return; }
  if (_daysInRange(from, to) > PERIOD_MAX_DAYS) { err.textContent = 'Oraliq 1 yildan oshmasligi kerak'; return; }
  _setPeriod({ from, to });
  _onPeriodChanged();
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('#periodNav')) _setPeriodPanel(false);
});
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || document.getElementById('periodPanel')?.hidden !== false) return;
  e.preventDefault(); // Esc faqat davr panelini yopadi, bo'lim sahifasini emas
  _setPeriodPanel(false, { returnFocus: true });
});

async function _fetchPeriodStats(query) {
  try {
    const res = await fetch(`${API_BASE}/stats/monthly/?${query}`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error('Monthly stats error:', e);
    return null;
  }
}

// Tanlangan davrning hamma operatsiyalari (bosh sahifadagi oxirgi 15 tasi emas)
async function _fetchPeriodOps(q) {
  try {
    const [expenses, incomes, transfers] = await Promise.all([
      _fetchAllPages(`${API_BASE}/expenses/?${q}`),
      _fetchAllPages(`${API_BASE}/incomes/?${q}`),
      _fetchAllPages(`${API_BASE}/transfers/?${q}`),
    ]);
    return { expenses, incomes, transfers };
  } catch (e) {
    console.error('Month operations error:', e);
    return { error: true };
  }
}

// silent: ro'yxat yangilanayotganda eskisi ko'rinib turadi ("Yuklanmoqda..." chiqib, sahifa sakramasligi uchun)
async function _loadMonthlyStats({ silent = false } = {}) {
  _updatePeriodLabel();
  const seq = ++_monthLoadSeq;
  const query = _periodQuery();

  if (_txPageMode === 'transactions') {
    if (!silent || !_monthOps) {
      _monthOps = null;
      renderTxPageList(); // "Yuklanmoqda..."
    }
    const ops = await _fetchPeriodOps(query);
    if (seq !== _monthLoadSeq) return; // shu orada boshqa davr tanlangan
    _monthOps = ops;
    renderTxPageList();
    return;
  }

  const stats = await _fetchPeriodStats(query);
  if (seq !== _monthLoadSeq) return;
  _statsData = stats;
  renderMonthlyTrendChart((_statsData && _statsData.daily_trend) || []);
  _renderStatsCategoryList('expense');
  _renderStatsCategoryList('income');
  warnMissingRates(_statsData && _statsData.missing_rates);
}

// ── Oylik chiziqli diagramma (Kirim/Chiqim trendi) ────────────

// Catmull-Rom nuqtalar orqali silliq egri chiziq (Bezier) yo'li quradi
function _smoothPath(points) {
  if (points.length < 2) return '';
  if (points.length === 2) return `M${points[0][0]},${points[0][1]} L${points[1][0]},${points[1][1]}`;
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`;
  }
  return d;
}

function renderMonthlyTrendChart(dailyTrend) {
  const wrapper = document.getElementById('monthlyTrendChart');
  if (!wrapper) return;

  const total = dailyTrend.reduce((sum, d) => sum + (d.income || 0) + (d.expense || 0), 0);
  if (!dailyTrend.length || total === 0) {
    wrapper.innerHTML = `<div class="weekly-rank-empty">${_statsRange ? 'Bu davr' : 'Bu oy'} uchun ma'lumot yo'q</div>`;
    return;
  }

  const width = 600, height = 170;
  const pL = 4, pR = 4, pT = 16, pB = 22;
  const chartW = width - pL - pR;
  const chartH = height - pT - pB;
  const n = dailyTrend.length;

  const incomes = dailyTrend.map(d => d.income || 0);
  const expenses = dailyTrend.map(d => d.expense || 0);
  const maxVal = Math.max(...incomes, ...expenses, 1);

  const xFor = (i) => pL + (n > 1 ? (i / (n - 1)) * chartW : chartW / 2);
  const yFor = (val) => pT + chartH - (val / maxVal) * chartH;
  const baseY = yFor(0);

  // Oraliq bir necha oyni qamrasa faqat kun raqami chalkashtiradi (1, 15, 1 ...) — "5-okt" ko'rinishida yoziladi
  const multiMonth = !!dailyTrend[0].date && dailyTrend[0].date.slice(0, 7) !== dailyTrend[n - 1].date.slice(0, 7);
  const labelStep = Math.ceil(n / 6);
  let xLabelsSvg = '';
  dailyTrend.forEach((d, i) => {
    if (i % labelStep === 0 || i === n - 1) {
      const text = multiMonth ? formatDate(_parseIsoDay(d.date)) : d.day;
      xLabelsSvg += `<text x="${xFor(i)}" y="${height - 6}" class="trend-axis-label" text-anchor="middle">${text}</text>`;
    }
  });

  const incPath = _smoothPath(incomes.map((v, i) => [xFor(i), yFor(v)]));
  const expPath = _smoothPath(expenses.map((v, i) => [xFor(i), yFor(v)]));
  const incAreaPath = `${incPath} L${xFor(n - 1)},${baseY} L${xFor(0)},${baseY} Z`;

  wrapper.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" class="trend-chart-svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id="trendIncomeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" class="trend-grad-stop-start" />
          <stop offset="100%" class="trend-grad-stop-end" />
        </linearGradient>
      </defs>
      <line x1="${pL}" y1="${baseY}" x2="${width - pR}" y2="${baseY}" class="trend-zero-line" />
      ${xLabelsSvg}
      <path d="${incAreaPath}" fill="url(#trendIncomeGrad)" />
      <path d="${expPath}" class="trend-line expense" />
      <path d="${incPath}" class="trend-line income" />
    </svg>
  `;
}

// ── Kategoriya ro'yxati ─────────────────────────────────────────
function _renderStatsCategoryList(type) {
  const isExp   = type === 'expense';
  const listId  = isExp ? 'statsCatExpList' : 'statsCatIncList';
  const totalId = isExp ? 'statsCatExpTotal' : 'statsCatIncTotal';
  const container = document.getElementById(listId);
  const totalEl   = document.getElementById(totalId);
  if (!container) return;

  const cats  = (_statsData && (isExp ? _statsData.category_expenses : _statsData.category_incomes)) || [];
  const total = (_statsData && (isExp ? _statsData.total_expense : _statsData.total_income)) || 0;

  // Server barcha valyutalarni Markaziy bank kursi bo'yicha shu valyutaga (so'm) o'girib, saralab beradi
  const cur = (_statsData && _statsData.stats_currency) || 'UZS';
  if (totalEl) totalEl.textContent = `${formatNumber(total)} ${cur}`;

  if (cats.length === 0) {
    container.innerHTML = `<div style="color:var(--text-subtle);font-size:0.82rem;padding:8px 0;">Ma'lumot yo'q</div>`;
    return;
  }

  const GRAD = isExp
    ? ['linear-gradient(90deg,#f43f5e,#fb7185)', 'linear-gradient(90deg,#f59e0b,#fbbf24)',
       'linear-gradient(90deg,#8b5cf6,#a78bfa)', 'linear-gradient(90deg,#06b6d4,#22d3ee)', 'linear-gradient(90deg,#ec4899,#f472b6)']
    : ['linear-gradient(90deg,#10b981,#34d399)', 'linear-gradient(90deg,#3b82f6,#60a5fa)',
       'linear-gradient(90deg,#06b6d4,#22d3ee)', 'linear-gradient(90deg,#8b5cf6,#a78bfa)', 'linear-gradient(90deg,#f59e0b,#fbbf24)'];

  container.innerHTML = cats.map((c, i) => `
    <div class="stats-cat-row">
      <div class="stats-cat-header">
        <span class="stats-cat-name">${escapeHtml(c.name)}</span>
        <span class="stats-cat-meta">${statsOriginalAmountHtml(c.parts, cur)}${formatNumber(c.total)} ${escapeHtml(cur)} <span class="stats-cat-percent">(${c.percent}%)</span></span>
      </div>
      <div class="stats-progress-track">
        <div class="stats-progress-fill" style="width:${Math.max(2, c.percent)}%;background:${GRAD[i % GRAD.length]};"></div>
      </div>
    </div>
  `).join('');
}

// ── 6. Operatsiyalar ro'yxati ──────────────────────────────────────
function renderTxPageList() {
  const container = document.getElementById('txPageList');
  if (!container) return;

  if (!_monthOps) {
    clearListPager('tx');
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Yuklanmoqda...</div>`;
    return;
  }
  if (_monthOps.error) {
    clearListPager('tx');
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">
      Amallarni yuklab bo'lmadi. <button type="button" class="btn btn-subtle btn-xs" data-action="loadMonthlyStats">Qayta urinish</button></div>`;
    return;
  }

  const list = _buildTxList(_txPageFilter, _monthOps);

  if (list.length === 0) {
    clearListPager('tx');
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Bu filtr bo'yicha amallar yo'q</div>`;
    return;
  }

  // Sana bo'yicha guruhlar faqat joriy sahifadagi yozuvlardan tuziladi; kun ikki sahifaga bo'linsa,
  // sarlavhasi keyingi sahifada ham chiqadi
  const groups = {};
  pageSlice('tx', list).forEach(item => {
    const d = new Date(item.date);
    const today     = new Date();
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    let label;
    if (d.toDateString() === today.toDateString())     label = 'Bugun';
    else if (d.toDateString() === yesterday.toDateString()) label = 'Kecha';
    else label = formatUzDate(d);
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  });

  let html = '';
  for (const [label, items] of Object.entries(groups)) {
    html += `<div class="tx-date-group">${label}</div>`;
    html += items.map(_txItemHtml).join('');
  }
  container.innerHTML = html;
}

// Davr navigatsiyasi (‹ ›)
document.getElementById('btnPrevMonth')?.addEventListener('click', () => _shiftPeriod(-1));
document.getElementById('btnNextMonth')?.addEventListener('click', () => _shiftPeriod(1));

// Tab switching inside tx page
document.addEventListener('click', e => {
  const tab = e.target.closest('#txPageTabs .tx-page-tab');
  if (!tab) return;
  _txPageFilter = tab.dataset.filter;
  resetListPage('tx');
  setNavActive(_txPageFilter);
  document.querySelectorAll('#txPageTabs .tx-page-tab').forEach(b => b.classList.remove('active'));
  tab.classList.add('active');
  renderTxPageList();
});





function openTxDetail(key, type, id) {
  const raw = _txDetailMap[key];
  if (!raw) return;

  const typeLabels = { expense: 'Chiqim', income: 'Kirim', transfer: "O'tkazma" };
  const icons      = { expense: 'expense', income: 'income', transfer: 'transfer' };
  const sign       = type === 'income' ? '+' : type === 'transfer' ? '' : '-';

  // Header
  const badge = document.getElementById('detailTypeBadge');
  badge.textContent = typeLabels[type] || type;
  badge.className = `detail-type-badge ${type}`;

  const titleEl = document.getElementById('detailTitle');
  if (type === 'expense')  titleEl.textContent = raw.category_name || 'Chiqim';
  if (type === 'income')   titleEl.textContent = raw.category_name || 'Kirim';
  if (type === 'transfer') titleEl.textContent = `${raw.from_wallet_name} → ${raw.to_wallet_name}`;

  // Amount
  const amtEl = document.getElementById('detailAmountBig');
  amtEl.textContent = sign + ((type === 'transfer' && transferAmountText(raw))
    || amountWithCurrency(raw.summa, type === 'transfer' ? raw.from_currency : raw.wallet_currency));
  amtEl.className = `detail-amount-big ${type}`;

  // Rows
  const rows = [];

  const addRow = (icon, label, val) => {
    if (val === undefined || val === null || val === '' || val === false) return;
    rows.push(`
      <div class="detail-row">
        <span class="detail-row-icon">${icon}</span>
        <span class="detail-row-label">${label}</span>
        <span class="detail-row-val">${escapeHtml(String(val))}</span>
      </div>
    `);
  };

  // Sana va qo'shilgan vaqt bitta qatorda: amal o'sha kuni kiritilgan bo'lsa vaqti ham ko'rsatiladi,
  // orqa sana bilan kiritilgan bo'lsa (vaqt chalg'itardi) — faqat tanlangan sana
  const addedSameDay = raw.created_at && formatUzDate(raw.created_at, { year: true }) === formatUzDate(raw.date, { year: true });
  const fullDate = formatUzDate(raw.date, { year: true });
  const dateText = addedSameDay ? formatUzDate(raw.created_at, { year: true, time: true }) : fullDate;

  if (type === 'expense') {
    addRow(icon('tag'), 'Turkum', raw.category_name);
    addRow(icon('wallet'), 'Hamyon', raw.wallet_name);
    addRow(memberIcon(raw.member_kind), 'Kimga', raw.member_name);
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', dateText);
  } else if (type === 'income') {
    addRow(icon('folder'), 'Manba', raw.category_name);
    addRow(icon('wallet'), 'Hamyon', raw.wallet_name);
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', dateText);
  } else if (type === 'transfer') {
    addRow(icon('up'), 'Chiqdi', raw.from_wallet_name);
    addRow(icon('down'), 'Tushdi', raw.to_wallet_name);
    if (transferAmountText(raw)) addRow(icon('transfer'), 'Kurs', formatRateText(raw.from_currency, raw.to_currency, Number(raw.rate)));
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', dateText);
  }

  document.getElementById('detailRows').innerHTML = rows.join('') ||
    '<p style="color:var(--text-subtle); font-size:0.83rem;">Qo\'shimcha ma\'lumot yo\'q</p>';

  document.getElementById('detailEditBtn').onclick = () => {
    closeTxDetail();
    openTxEdit(type, id, raw);
  };

  // Delete button
  const delBtn = document.getElementById('detailDeleteBtn');
  delBtn.onclick = () => {
    closeTxDetail();
    deleteTransaction(type, id);
  };

  // Show backdrop
  document.getElementById('txDetailBackdrop').classList.add('active');
}

function closeTxDetail(event) {
  if (event && event.target !== document.getElementById('txDetailBackdrop')) return;
  document.getElementById('txDetailBackdrop').classList.remove('active');
}
// Qorong'i fon bosilsa oyna yopiladi (oyna ichidagi bosishlar e'tiborsiz qoladi)
document.getElementById('txDetailBackdrop')?.addEventListener('click', closeTxDetail);


// Backenddagi DEBT_DUE_SOON_DAYS bilan mos bo'lishi kerak (views.py)
const DEBT_DUE_SOON_DAYS = 3;
const DEBT_URGENCY_RANK = { overdue: 0, soon: 1, normal: 2, none: 3 };

function _debtUrgency(d) {
  if (d.is_settled || !d.due_date) return 'none';
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const due = new Date(d.due_date + 'T00:00:00');
  const diffDays = Math.round((due - today) / 86400000);
  if (diffDays < 0) return 'overdue';
  if (diffDays <= DEBT_DUE_SOON_DAYS) return 'soon';
  return 'normal';
}

function _debtDueBadge(d) {
  if (!d.due_date) return '';
  const urgency = _debtUrgency(d);
  const label = urgency === 'overdue' ? `Muddati o'tgan: ${formatDueDate(d)}` : `Muddat: ${formatDueDate(d)}`;
  return `· <span class="debt-due-badge debt-due-${urgency}">${label}</span>`;
}

function renderDebts() {
  renderNotifications();
  const container = document.getElementById('debtsList');
  if (!container) return;

  if (state.debts.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Qarzlar mavjud emas</p>`;
    return;
  }

  // Bosh sahifada nechta hamyon bo'lsa, shuncha qarz (yonidagi "Hamyonlar" kartochkasi bilan bo'yi teng turadi).
  // Avval to'lanmaganlar (shoshilinchi tepada, keyin yangi yozilgani), joy qolsa — yopilganlar, oxirgi
  // harakati (to'lov) bo'yicha yangisi birinchi. Hammasi "Qarzlar tarixi"da
  const limit = Math.max(1, Math.min(state.wallets.length, HOME_WALLETS_LIMIT));
  const open = state.debts.filter(d => !d.is_settled).sort((a, b) =>
    DEBT_URGENCY_RANK[_debtUrgency(a)] - DEBT_URGENCY_RANK[_debtUrgency(b)]
    || new Date(b.created_at) - new Date(a.created_at));
  const settled = state.debts.filter(d => d.is_settled)
    .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  const latest = [...open, ...settled].slice(0, limit);

  container.innerHTML = latest.map(d => {
    const isGive = d.debt_type === 'give';
    const typeLabel = isGive ? 'Qarz berdim' : 'Qarz oldim';
    const typeColor = isGive ? 'var(--emerald)' : 'var(--amber)';

    return `
      <div class="debt-compact-card">
        <div class="debt-compact-info">
          <div style="font-weight: 500; font-size: 0.92rem; color: var(--text-main);">
            ${escapeHtml(d.person_name)}
            <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 6px; background: var(--bg-sunken); color: ${typeColor}; margin-left: 6px;">${typeLabel}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--text-subtle); margin-top: 2px;">
            Qoldiq: <b style="color:var(--text-main);">${formatNumber(d.remaining_summa)} ${debtCurrency(d)}</b> ${_debtDueBadge(d)}
          </div>
        </div>
        <div class="debt-compact-actions" style="display: flex; align-items: center; gap: 8px;">
          ${!d.is_settled ? `
            <button class="btn btn-subtle btn-xs" data-action="openRepayModal" data-args="${actionArgs(d.id)}">To'lash</button>
          ` : `<span style="font-size: 0.75rem; color: var(--emerald);">Yopildi ${icon('check')}</span>`}
          <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.75rem;" title="O'chirish" data-action="deleteDebt" data-args="${actionArgs(d.id)}">${icon('trash')}</button>
        </div>
      </div>
    `;
  }).join('');
}

// Qarzlar kartochkasining istalgan joyiga bosilsa daftar ochiladi (ichidagi tugmalar o'z ishini qiladi)
document.getElementById('debtsCard')?.addEventListener('click', (e) => {
  if (e.target.closest('button, a, input, select')) return;
  openDebtsPage();
});

// Hamyonlar kartochkasining istalgan joyiga bosilsa barcha hamyonlar ochiladi. Tugmalar va hamyon qatorlari
// o'z handleriga ega — ularni o'tkazib yuboramiz
document.getElementById('walletsCard')?.addEventListener('click', (e) => {
  if (e.target.closest('button, a, input, select, [data-action], .wallet-compact-card')) return;
  openWalletsPage();
});

// ==========================================
// DROPDOWN POPULATORS
// ==========================================

function populateWalletDropdowns() {
  const dropdownIds = [
    'expenseWalletSelect',
    'incomeWalletSelect',
    'transferFromWallet',
    'transferToWallet',
    'debtWalletSelect',
    'repayWalletSelect'
  ];

  // Maqsad hamyonidan pul chiqmaydi va unga faqat O'tkazma tushadi — u faqat "Qaysi hamyonga" ro'yxatida
  const spendable = spendableWallets();
  dropdownIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    // "Qaysi hamyonga" ro'yxati "Qaysi hamyondan" dan keyin quriladi — tanlangan chiqim hamyoni unda bo'lmaydi
    if (id === 'transferToWallet') {
      syncTransferTargets();
      return;
    }

    const currentVal = el.value;
    el.innerHTML = spendable.map(walletOptionHtml).join('');
    if (currentVal && Array.from(el.options).some(o => o.value === currentVal)) {
      el.value = currentVal;
    }
  });

  updateSingleWalletFieldVisibility();
  updateTransferButtonVisibility();
  updateDebtCurrencyField();
  updateAmountLabels();
}

// Summa yorlig'iga tanlangan hamyon valyutasi qo'shiladi: "Summa (USD) *"
const AMOUNT_LABELS = [
  { selectId: 'expenseWalletSelect', labelId: 'expenseSummaLabel', text: 'Miqdor' },
  { selectId: 'incomeWalletSelect', labelId: 'incomeSummaLabel', text: 'Kirim miqdori' },
];
function updateAmountLabels() {
  AMOUNT_LABELS.forEach(({ selectId, labelId, text }) => {
    const label = document.getElementById(labelId);
    const select = document.getElementById(selectId);
    if (!label || !select) return;
    const wallet = state.wallets.find(w => String(w.id) === select.value);
    label.textContent = wallet ? `${text} (${wallet.currency}) *` : `${text} *`;
  });
}
AMOUNT_LABELS.forEach(({ selectId }) => {
  document.getElementById(selectId)?.addEventListener('change', updateAmountLabels);
});

// Hamyon bitta bo'lsa, "Qaysi hamyondan/ga?" savolini yashiramiz — tanlov qilib
// o'tirishning hojati yo'q, yagona hamyon avtomatik tanlanadi.
function walletOptionHtml(w) {
  return `<option value="${w.id}">${escapeHtml(w.name)} (${formatMoney(w.summa, w.currency)})</option>`;
}

// "Qaysi hamyonga" ro'yxati: "Qaysi hamyondan" da tanlangan hamyondan boshqa barcha hamyonlar (maqsad hamyonlari ham).
// Bank → Bank kabi o'zidan o'ziga o'tkazmani tanlab bo'lmaydi; avvalgi tanlov iloji bo'lsa saqlanadi
function syncTransferTargets() {
  const from = document.getElementById('transferFromWallet');
  const to = document.getElementById('transferToWallet');
  if (!from || !to) return;
  const keep = to.value;
  to.innerHTML = state.wallets.filter(w => String(w.id) !== from.value).map(walletOptionHtml).join('');
  if (keep && [...to.options].some(o => o.value === keep)) to.value = keep;
  to._csSync?.();
}

// Xarajat, kirim, qarz va chiqim o'tkazmasi uchun tanlanadigan hamyonlar (maqsad hamyonlarisiz)
function spendableWallets() {
  return state.wallets.filter(w => !w.is_goal);
}

function updateSingleWalletFieldVisibility() {
  const spendable = spendableWallets();
  const singleWallet = spendable.length === 1;
  [
    { groupId: 'expenseWalletGroup', selectId: 'expenseWalletSelect' },
    { groupId: 'incomeWalletGroup', selectId: 'incomeWalletSelect' },
  ].forEach(({ groupId, selectId }) => {
    const group = document.getElementById(groupId);
    const select = document.getElementById(selectId);
    if (!group || !select) return;
    group.style.display = singleWallet ? 'none' : '';
    select.required = !singleWallet;
    if (singleWallet) {
      select.value = String(spendable[0].id);
    }
  });
}

// Kamida 2 ta hamyon bo'lmasa, "O'tkazma" tezkor tugmasi ma'nosiz bo'ladi
// (qaysidan va qaysiga ko'chirish kerakligini tanlashning iloji yo'q).
function updateTransferButtonVisibility() {
  const btn = document.getElementById('btnOpenTransferModal');
  const grid = document.querySelector('.action-grid-row');
  if (!btn || !grid) return;
  const hasEnoughWallets = state.wallets.length >= 2 && spendableWallets().length >= 1;
  btn.style.display = hasEnoughWallets ? '' : 'none';
  grid.classList.toggle('cols-3', !hasEnoughWallets);
}

// ── Toifalarni sozlash: qo'shish / o'chirish / qaytarish ──────────
const CATEGORY_API = { expense: 'expense-categories', income: 'categories' };
let _catKind = 'expense';
let _catItems = [];

function openCategoryManager(kind) {
  _catKind = kind;
  document.querySelectorAll('#catKindTabs .cat-tab').forEach(b => b.classList.toggle('active', b.dataset.kind === kind));
  document.getElementById('formAddCategory').reset();
  openModal('modalCategories');
  loadCategoryManager();
}

async function loadCategoryManager() {
  const kind = _catKind;
  let items = [];
  try {
    const res = await fetch(`${API_BASE}/${CATEGORY_API[kind]}/?include_hidden=1`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    items = data.results || data;
  } catch (err) {
    console.error('Category manager fetch error:', err);
    showToast("Turkumlarni yuklab bo'lmadi", 'error');
  }
  if (kind !== _catKind) return; // foydalanuvchi boshqa tabga o'tib ketgan
  _catItems = items;
  renderCategoryManager();
}

function renderCategoryManager() {
  const visible = _catItems.filter(c => !c.hidden);
  const hidden = _catItems.filter(c => c.hidden);

  // Nomning o'zi tahrirlanadi: bosib yoziladi, Enter yoki tashqariga bosish — saqlash, Esc — bekor qilish
  document.getElementById('categoryManagerList').innerHTML = visible.length
    ? visible.map(c => `
      <div class="cat-row">
        <input type="text" class="cat-name-input" data-cat-name="${c.id}" value="${escapeHtml(c.name)}"
               maxlength="255" spellcheck="false" autocomplete="off" aria-label="Turkum nomi" title="Nomini o'zgartirish uchun bosing">
        ${c.is_custom ? '<span class="cat-badge">Mening turkumim</span>' : ''}
        <button type="button" class="btn-icon" title="O'chirish" data-cat-delete="${c.id}">${icon('trash')}</button>
      </div>`).join('')
    : `<div class="cat-empty">Turkumlar yo'q. Yuqoridan yangisini qo'shing.</div>`;

  document.getElementById('hiddenCategoriesBox').hidden = hidden.length === 0;
  document.getElementById('hiddenCatCount').textContent = hidden.length;
  document.getElementById('hiddenCategoryList').innerHTML = hidden.map(c => `
    <div class="cat-row">
      <span class="cat-name">${escapeHtml(c.name)}</span>
      <button type="button" class="btn btn-subtle btn-xs" data-cat-restore="${c.id}">Qaytarish</button>
    </div>`).join('');
}

// Sozlash oynasi va Kirim/Harajat formalaridagi tanlagich birga yangilanadi
function refreshCategoryViews() {
  return Promise.all([loadCategoryManager(), fetchCategories()]);
}

document.getElementById('catKindTabs')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.cat-tab');
  if (!btn || btn.dataset.kind === _catKind) return;
  _catKind = btn.dataset.kind;
  document.querySelectorAll('#catKindTabs .cat-tab').forEach(b => b.classList.toggle('active', b === btn));
  loadCategoryManager();
});

onSubmitOnce('formAddCategory', async (e) => {
  e.preventDefault();
  const input = document.getElementById('newCategoryName');
  const name = input.value.trim();
  if (!name) return;
  try {
    const res = await fetch(`${API_BASE}/${CATEGORY_API[_catKind]}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      input.value = '';
      showToast(`«${name}» turkumi qo'shildi`);
      await refreshCategoryViews();
    } else {
      showToast(extractErrorMessage(data, "Turkum qo'shishda xatolik"), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

document.getElementById('modalCategories')?.addEventListener('click', async (e) => {
  const delBtn = e.target.closest('[data-cat-delete]');
  const restoreBtn = e.target.closest('[data-cat-restore]');

  if (delBtn) {
    const cat = _catItems.find(c => c.id === Number(delBtn.dataset.catDelete));
    if (!cat) return;
    const message = cat.is_custom
      ? `«${cat.name}» turkumi o'chiriladi. Oldingi amallaringizda nomi saqlanib qoladi.`
      : `«${cat.name}» umumiy turkum faqat sizning ro'yxatingizdan olib tashlanadi. Boshqa foydalanuvchilarga ta'sir qilmaydi, keyin qaytarishingiz mumkin.`;
    if (!(await confirmDelete(message))) return;
    try {
      const res = await fetch(`${API_BASE}/${CATEGORY_API[_catKind]}/${cat.id}/`, { method: 'DELETE' });
      if (res.ok) {
        showToast("Turkum o'chirildi");
        await refreshCategoryViews();
      } else {
        showToast(extractErrorMessage(await res.json().catch(() => ({})), "Turkumni o'chirishda xatolik"), 'error');
      }
    } catch (err) {
      showToast(NETWORK_ERROR_MESSAGE, 'error');
    }
  }

  if (restoreBtn) {
    try {
      const res = await fetch(`${API_BASE}/${CATEGORY_API[_catKind]}/${Number(restoreBtn.dataset.catRestore)}/restore/`, { method: 'POST' });
      if (res.ok) {
        showToast('Turkum qaytarildi');
        await refreshCategoryViews();
      } else {
        showToast(extractErrorMessage(await res.json().catch(() => ({})), 'Turkumni qaytarishda xatolik'), 'error');
      }
    } catch (err) {
      showToast(NETWORK_ERROR_MESSAGE, 'error');
    }
  }
});

// ── Toifa nomini joyida o'zgartirish (tugmasiz) ──────────────────
// Umumiy toifa nomini oddiy foydalanuvchi o'zgartirsa, server unga shaxsiy nusxa yaratadi —
// boshqa foydalanuvchilarda nom o'zgarmaydi (views.py: PersonalCategoryMixin._personalize_global)
async function saveCategoryName(input) {
  const id = Number(input.dataset.catName);
  const cat = _catItems.find(c => c.id === id);
  if (!cat || input.dataset.saving) return;
  const name = input.value.trim();
  if (!name || name === cat.name) {
    input.value = cat.name; // bo'sh yoki o'zgarmagan nom — eski holiga qaytadi
    return;
  }

  input.dataset.saving = '1';
  input.classList.add('saving');
  try {
    const res = await fetch(`${API_BASE}/${CATEGORY_API[_catKind]}/${id}/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(`Turkum nomi «${name}» ga o'zgartirildi`);
      // Eski operatsiyalar va formalardagi tanlagichlarda ham yangi nom ko'rinishi uchun hammasi yangilanadi
      await Promise.all([loadCategoryManager(), refreshAll()]);
    } else {
      showToast(extractErrorMessage(data, "Turkum nomini o'zgartirishda xatolik"), 'error');
      input.value = cat.name;
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
    input.value = cat.name;
  } finally {
    delete input.dataset.saving;
    input.classList.remove('saving');
  }
}

const categoryList = document.getElementById('categoryManagerList');
// "change" maydondan chiqilganda (Enter yoki tashqariga bosish) va qiymat o'zgargan bo'lsagina ishlaydi
categoryList?.addEventListener('change', (e) => {
  if (e.target.matches('[data-cat-name]')) saveCategoryName(e.target);
});
categoryList?.addEventListener('keydown', (e) => {
  if (!e.target.matches('[data-cat-name]')) return;
  if (e.key === 'Enter') {
    e.preventDefault();
    e.target.blur();
  } else if (e.key === 'Escape') {
    // Oyna yopilmasin — faqat tahrir bekor qilinadi
    e.stopPropagation();
    const cat = _catItems.find(c => c.id === Number(e.target.dataset.catName));
    if (cat) e.target.value = cat.name;
    e.target.blur();
  }
});

function populateExpenseCategoryDropdown() {
  const el = document.getElementById('expenseCategorySelect');
  if (!el) return;
  const previous = el.value;
  const options = [
    '<option value="" disabled selected>-- Chiqim turkumini tanlang --</option>',
    ...state.expenseCategories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`),
    '<option value="__custom__">Boshqa (o\'zingiz yozing...)</option>'
  ];
  el.innerHTML = options.join('');
  if (previous && [...el.options].some(o => o.value === previous)) el.value = previous;
  if (el._csSync) el._csSync();
}

function populateIncomeCategoryDropdown() {
  const el = document.getElementById('incomeCategorySelect');
  if (!el) return;
  const previous = el.value;
  const options = [
    '<option value="" disabled selected>-- Kirim manbayini tanlang --</option>',
    ...state.incomeCategories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`),
    '<option value="__custom__">Boshqa (o\'zingiz yozing...)</option>'
  ];
  el.innerHTML = options.join('');
  if (previous && [...el.options].some(o => o.value === previous)) el.value = previous;
  if (el._csSync) el._csSync();
}

// Custom category change listeners
document.getElementById('incomeCategorySelect')?.addEventListener('change', (e) => {
  const group = document.getElementById('incomeCustomCategoryGroup');
  const input = document.getElementById('incomeCustomCategory');
  if (e.target.value === '__custom__') {
    group.style.display = 'block';
    input.required = true;
    input.focus();
  } else {
    group.style.display = 'none';
    input.required = false;
    input.value = '';
  }
});

document.getElementById('expenseCategorySelect')?.addEventListener('change', (e) => {
  const group = document.getElementById('expenseCustomCategoryGroup');
  const input = document.getElementById('expenseCustomCategory');
  if (e.target.value === '__custom__') {
    group.style.display = 'block';
    input.required = true;
    input.focus();
  } else {
    group.style.display = 'none';
    input.required = false;
    input.value = '';
  }
});

// ==========================================
// FORM SUBMISSIONS & ERROR HANDLING
// ==========================================

// Error extraction helper
function extractErrorMessage(err, fallback = 'Xatolik yuz berdi') {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (err.error) return Array.isArray(err.error) ? err.error[0] : err.error;
  if (err.detail) return Array.isArray(err.detail) ? err.detail[0] : err.detail;
  if (err.summa) return Array.isArray(err.summa) ? err.summa[0] : err.summa;
  if (err.wallet) return Array.isArray(err.wallet) ? err.wallet[0] : err.wallet;
  if (err.to_wallet) return Array.isArray(err.to_wallet) ? err.to_wallet[0] : err.to_wallet;
  if (err.from_wallet) return Array.isArray(err.from_wallet) ? err.from_wallet[0] : err.from_wallet;
  if (err.name) return Array.isArray(err.name) ? err.name[0] : err.name;
  const firstKey = Object.keys(err)[0];
  if (firstKey) {
    const val = err[firstKey];
    return Array.isArray(val) ? val[0] : String(val);
  }
  return fallback;
}

// Yangi toifa yaratildi, lekin operatsiya hali saqlanmagan (masalan balans yetmasligi mumkin) —
// tanlagich yangi toifaga o'tkaziladi, qayta yuborishda toifa ikkinchi marta yaratilmaydi
function selectCreatedCategory(selectId, categoryId) {
  const select = document.getElementById(selectId);
  select.value = String(categoryId);
  // "change" "Boshqa" maydonini yashiradi va tozalaydi; _csSync ko'rinadigan tanlagichni yangilaydi
  select.dispatchEvent(new Event('change', { bubbles: true }));
  if (select._csSync) select._csSync();
}

// ── Kirim / harajat / o'tkazma: qo'shish va tahrirlash bitta oynada ──────────
// Tahrirlashda oyna eski qiymatlar bilan ochiladi, form.dataset.editId bo'ladi va saqlash PATCH yuboradi.
// Balans server tomonida sof farq bilan to'g'rilanadi (models.py: apply_wallet_changes)
const TX_FORMS = {
  expense:  { modal: 'modalExpense',  form: 'formAddExpense',  api: 'expenses',
              addTitle: 'Chiqim yozish', editTitle: 'Chiqimni tahrirlash', addSubmit: 'Saqlash' },
  income:   { modal: 'modalIncome',   form: 'formAddIncome',   api: 'incomes',
              addTitle: 'Kirim yozish', editTitle: 'Kirimni tahrirlash', addSubmit: 'Kirimni saqlash' },
  transfer: { modal: 'modalTransfer', form: 'formAddTransfer', api: 'transfers',
              addTitle: "Hamyondan hamyonga o'tkazma", editTitle: "O'tkazmani tahrirlash", addSubmit: "O'tkazish" },
};
// Tahrirlanayotgan yozuv: { type, id, raw } yoki null (yangi qo'shish)
let _txEdit = null;

// Saqlangan vaqt (ISO) -> <input type="date"> qiymati, foydalanuvchining mahalliy kunida
function isoToDateInput(iso) {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

function setTxFormMode(type, editing) {
  const cfg = TX_FORMS[type];
  const modal = document.getElementById(cfg.modal);
  modal.querySelector('[data-tx-title]').textContent = editing ? cfg.editTitle : cfg.addTitle;
  modal.querySelector('[data-tx-submit]').textContent = editing ? "O'zgarishlarni saqlash" : cfg.addSubmit;
}

// Tanlagichda yo'q qiymat (o'chirilgan toifa yoki a'zo) — eski nomi bilan vaqtincha qo'shiladi, aks holda
// tahrir oynasida bo'sh ko'rinib, foydalanuvchi bilmasdan boshqasiga almashtirib yuborardi
function selectValueOrKeep(selectId, value, label) {
  const el = document.getElementById(selectId);
  if (!el) return;
  const v = value == null ? '' : String(value);
  if (v && ![...el.options].some(o => o.value === v)) {
    el.add(new Option(label || '—', v), el.options[1] || null);
  }
  el.value = v;
  el.dispatchEvent(new Event('change', { bubbles: true }));
  if (el._csSync) el._csSync();
}

function openTxEdit(type, id, raw) {
  const cfg = TX_FORMS[type];
  const form = document.getElementById(cfg.form);
  form.reset();
  _txEdit = { type, id, raw };
  form.dataset.editId = id;

  if (type === 'expense') {
    document.getElementById('expenseSumma').value = raw.summa;
    selectValueOrKeep('expenseWalletSelect', raw.wallet, raw.wallet_name);
    selectValueOrKeep('expenseCategorySelect', raw.category, raw.category_name);
    selectValueOrKeep('expenseMemberSelect', raw.member, raw.member_name);
    document.getElementById('expenseDate').value = isoToDateInput(raw.date);
    document.getElementById('expenseDescription').value = raw.description || '';
  } else if (type === 'income') {
    document.getElementById('incomeSumma').value = raw.summa;
    selectValueOrKeep('incomeWalletSelect', raw.wallet, raw.wallet_name);
    selectValueOrKeep('incomeCategorySelect', raw.category, raw.category_name);
    document.getElementById('incomeDate').value = isoToDateInput(raw.date);
    document.getElementById('incomeDescription').value = raw.description || '';
  } else {
    selectValueOrKeep('transferFromWallet', raw.from_wallet, raw.from_wallet_name);
    selectValueOrKeep('transferToWallet', raw.to_wallet, raw.to_wallet_name);
    document.getElementById('transferSumma').value = raw.summa;
    document.getElementById('transferDescription').value = raw.description || '';
  }
  setTxFormMode(type, true);
  openModal(cfg.modal);
}

// Oyna yopilganda tahrir rejimi tugaydi: keyingi "Kirim"/"Harajat" bosilishi bo'sh forma bilan ochilsin
Object.entries(TX_FORMS).forEach(([type, cfg]) => {
  const modal = document.getElementById(cfg.modal);
  if (!modal) return;
  modal._onClose = () => {
    const form = document.getElementById(cfg.form);
    if (!form.dataset.editId) return;
    delete form.dataset.editId;
    if (_txEdit?.type === type) _txEdit = null;
    form.reset();
    setTxFormMode(type, false);
    // Tahrir uchun vaqtincha qo'shilgan (o'chirilgan) toifa/a'zo/hamyon variantlari olib tashlansin
    populateWalletDropdowns();
    populateExpenseCategoryDropdown();
    populateIncomeCategoryDropdown();
    populateExpenseMemberDropdown();
  };
});

// Yangi yozuv — POST, tahrir — PATCH. Tahrirda sana o'zgarmagan bo'lsa yuborilmaydi: aks holda asl vaqt
// (bir kundagi yozuvlar tartibi) hozirgi vaqtga almashib qolardi
async function sendTx(type, payload, dateVal) {
  const cfg = TX_FORMS[type];
  const editing = _txEdit?.type === type ? _txEdit : null;
  if (dateVal && !(editing && dateVal === isoToDateInput(editing.raw.date))) {
    payload.date = dateInputToISO(dateVal);
  }
  const url = editing ? `${API_BASE}/${cfg.api}/${editing.id}/` : `${API_BASE}/${cfg.api}/`;
  return fetch(url, {
    method: editing ? 'PATCH' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

// 1. Add Expense
onSubmitOnce('formAddExpense', async (e) => {
  e.preventDefault();
  let categoryId = document.getElementById('expenseCategorySelect').value;

  if (!categoryId) {
    showToast('Iltimos, xarajat turkumini tanlang', 'error');
    return;
  }

  // Agar yangi kategoriya yozilgan bo'lsa
  if (categoryId === '__custom__') {
    const customName = document.getElementById('expenseCustomCategory').value.trim();
    if (!customName) {
      showToast('Iltimos, xarajat turkumi nomini yozing', 'error');
      return;
    }

    try {
      const catRes = await fetch(`${API_BASE}/expense-categories/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: customName })
      });
      if (catRes.ok) {
        const catData = await catRes.json();
        categoryId = catData.id;
        await fetchCategories();
        selectCreatedCategory('expenseCategorySelect', categoryId);
      } else {
        const errData = await catRes.json().catch(() => ({}));
        showToast(extractErrorMessage(errData, 'Turkum yaratishda xatolik'), 'error');
        return;
      }
    } catch (err) {
      showToast(NETWORK_ERROR_MESSAGE, 'error');
      return;
    }
  }

  const payload = {
    summa: readAmount('expenseSumma'),
    wallet: parseInt(document.getElementById('expenseWalletSelect').value),
    category: parseInt(categoryId),
    description: document.getElementById('expenseDescription').value.trim(),
  };

  // Tahrirda "O'zim uchun" tanlansa a'zo olib tashlanishi kerak — shuning uchun bo'sh qiymat ham null bo'lib yuboriladi
  const memberVal = document.getElementById('expenseMemberSelect')?.value;
  payload.member = memberVal ? parseInt(memberVal) : null;

  const editing = !!_txEdit;
  try {
    const res = await sendTx('expense', payload, document.getElementById('expenseDate')?.value);

    if (res.ok) {
      showToast(editing ? "Chiqim o'zgartirildi" : 'Chiqim muvaffaqiyatli saqlandi!');
      closeModal('modalExpense');
      e.target.reset();
      document.getElementById('expenseCustomCategoryGroup').style.display = 'none';
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Chiqim saqlashda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 2. Add Income
onSubmitOnce('formAddIncome', async (e) => {
  e.preventDefault();
  let categoryId = document.getElementById('incomeCategorySelect').value;

  if (!categoryId) {
    showToast('Iltimos, kirim manbayini tanlang', 'error');
    return;
  }

  // Agar yangi manba yozilgan bo'lsa
  if (categoryId === '__custom__') {
    const customName = document.getElementById('incomeCustomCategory').value.trim();
    if (!customName) {
      showToast('Iltimos, kirim manbayi nomini yozing', 'error');
      return;
    }

    try {
      const catRes = await fetch(`${API_BASE}/categories/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: customName })
      });
      if (catRes.ok) {
        const catData = await catRes.json();
        categoryId = catData.id;
        await fetchCategories();
        selectCreatedCategory('incomeCategorySelect', categoryId);
      } else {
        const errData = await catRes.json().catch(() => ({}));
        showToast(extractErrorMessage(errData, 'Manba yaratishda xatolik'), 'error');
        return;
      }
    } catch (err) {
      showToast(NETWORK_ERROR_MESSAGE, 'error');
      return;
    }
  }

  const payload = {
    summa: readAmount('incomeSumma'),
    wallet: parseInt(document.getElementById('incomeWalletSelect').value),
    category: parseInt(categoryId),
    description: document.getElementById('incomeDescription').value.trim(),
  };

  const editing = !!_txEdit;
  try {
    const res = await sendTx('income', payload, document.getElementById('incomeDate')?.value);

    if (res.ok) {
      showToast(editing ? "Kirim o'zgartirildi" : 'Kirim muvaffaqiyatli saqlandi!');
      closeModal('modalIncome');
      e.target.reset();
      document.getElementById('incomeCustomCategoryGroup').style.display = 'none';
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Kirim saqlashda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 3. Add Transfer
onSubmitOnce('formAddTransfer', async (e) => {
  e.preventDefault();
  const fromW = parseInt(document.getElementById('transferFromWallet').value);
  const toW = parseInt(document.getElementById('transferToWallet').value);
  const summa = readAmount('transferSumma');

  if (fromW === toW) {
    showToast('Bir xil hamyonlar o\'rtasida o\'tkazma qilib bo\'lmaydi', 'error');
    return;
  }

  const payload = {
    from_wallet: fromW,
    to_wallet: toW,
    summa: summa,
    description: document.getElementById('transferDescription').value.trim(),
    user: state.currentUserId
  };
  // Valyutalar har xil bo'lsa: summa kiritilmasa server Markaziy bank kursi bo'yicha o'zi hisoblaydi
  const toSummaRaw = document.getElementById('transferToSumma').value;
  if (document.getElementById('transferToSummaGroup').style.display !== 'none' && toSummaRaw) {
    payload.to_summa = readAmount('transferToSumma');
  }

  const editing = !!_txEdit;
  if (editing) delete payload.user;
  try {
    const res = await sendTx('transfer', payload);

    if (res.ok) {
      showToast(editing ? "O'tkazma o'zgartirildi" : 'O\'tkazma muvaffaqiyatli amalga oshirildi!');
      closeModal('modalTransfer');
      e.target.reset();
      document.getElementById('transferToSummaGroup').style.display = 'none';
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'O\'tkazmada xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 4. Add Debt
onSubmitOnce('formAddDebt', async (e) => {
  e.preventDefault();
  const walletVal = document.getElementById('debtWalletSelect').value;
  const payload = {
    person_name: document.getElementById('debtPersonName').value.trim(),
    debt_type: document.getElementById('debtTypeSelect').value,
    summa: readAmount('debtSumma'),
    due_date: document.getElementById('debtDueDate').value || null,
    wallet: parseInt(walletVal),
    description: document.getElementById('debtDescription').value.trim(),
    user: state.currentUserId
  };

  try {
    const res = await fetch(`${API_BASE}/debts/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Qarz daftarga yozildi!');
      closeModal('modalDebt');
      e.target.reset();
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarz kiritishda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 5. Add Wallet
onSubmitOnce('formAddWallet', async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById('walletName').value.trim(),
    summa: readAmount('walletInitialSumma') || 0,
    currency: document.getElementById('walletCurrency').value.trim() || 'UZS',
    user: state.currentUserId
  };

  try {
    const res = await fetch(`${API_BASE}/wallets/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Yangi hamyon qo\'shildi!');
      closeModal('modalWallet');
      e.target.reset();
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Hamyon yaratishda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 6. Add Member
onSubmitOnce('formAddMember', async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById('memberName').value.trim(),
    kind: document.getElementById('memberKind')?.value || 'person',
  };

  try {
    const res = await fetch(`${API_BASE}/members/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Yangi a\'zo qo\'shildi!');
      closeModal('modalMember');
      e.target.reset();
      await fetchMembers();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'A\'zo qo\'shishda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// 7. Repay Debt
let activeRepayDebtId = null;
function openRepayModal(debtId) {
  const debt = state.debts.find(d => d.id === debtId);
  if (!debt) return;
  activeRepayDebtId = debtId;
  document.getElementById('repayPersonName').textContent = debt.person_name;
  document.getElementById('repayRemaining').textContent = formatMoney(debt.remaining_summa, debt.currency || 'UZS');
  document.querySelector('label[for="repayAmount"]').textContent = `To'lov Miqdori (${debt.currency || 'UZS'}) *`;
  document.getElementById('repayAmount').max = debt.remaining_summa;
  document.getElementById('repayAmount').value = debt.remaining_summa;
  // Qarz valyutasidagi hamyon bo'lsa, shuni oldindan tanlaymiz
  const repaySelect = document.getElementById('repayWalletSelect');
  const sameCurrency = state.wallets.find(w => w.currency === (debt.currency || 'UZS'));
  if (sameCurrency && state.wallets.find(w => String(w.id) === repaySelect.value)?.currency !== sameCurrency.currency) {
    repaySelect.value = String(sameCurrency.id);
    repaySelect._csSync?.();
  }
  openModal('modalRepayDebt');
  updateRepayConvertHint();
}

// Qarz va hamyon valyutasi har xil bo'lsa: hamyonga kurs bo'yicha qancha yozilishini ko'rsatamiz
let _repayHintSeq = 0;
async function updateRepayConvertHint() {
  const hint = document.getElementById('repayConvertHint');
  if (!hint) return;
  const debt = state.debts.find(d => d.id === activeRepayDebtId);
  const wallet = state.wallets.find(w => w.id === parseInt(document.getElementById('repayWalletSelect').value));
  const amount = readAmount('repayAmount') || 0;
  const seq = ++_repayHintSeq;
  if (!debt || !wallet || (debt.currency || 'UZS') === wallet.currency || amount <= 0) {
    hint.textContent = '';
    return;
  }
  const verb = debt.debt_type === 'give' ? "qo'shiladi" : 'yechiladi';
  try {
    const debtCur = debt.currency || 'UZS';  // yuqoridagi tekshiruv ham shu zaxira bilan; aks holda "undefined" yuborilardi
    const q = `from=${encodeURIComponent(debtCur)}&to=${encodeURIComponent(wallet.currency)}&amount=${amount}`;
    const res = await fetch(`${API_BASE}/rates/convert/?${q}`);
    const data = await res.json().catch(() => ({}));
    if (seq !== _repayHintSeq) return;
    hint.textContent = res.ok
      ? `Hamyonga Markaziy bank kursi bo'yicha ${formatNumber(data.result)} ${wallet.currency} ${verb} (${formatRateText(debtCur, wallet.currency, Number(data.rate))}).`
      : `${debtCur} → ${wallet.currency} kursini aniqlab bo'lmadi.`;
  } catch (err) {
    if (seq === _repayHintSeq) hint.textContent = '';
  }
}
document.getElementById('repayWalletSelect')?.addEventListener('change', updateRepayConvertHint);
document.getElementById('repayAmount')?.addEventListener('input', () => {
  clearTimeout(updateRepayConvertHint._t);
  updateRepayConvertHint._t = setTimeout(updateRepayConvertHint, 300);
});

// ==========================================
// O'TKAZMA: VALYUTA KURSI
// ==========================================

// Hamyonlar valyutasi har xil bo'lsa "Tushadigan summa" maydoni chiqadi va kurs bo'yicha hisob ko'rsatiladi.
// Maydon bo'sh qoldirilsa server Markaziy bank kursi bilan o'zi hisoblaydi
let _transferPreviewSeq = 0;
async function updateTransferCurrencyPreview() {
  const fromW = state.wallets.find(w => w.id === parseInt(document.getElementById('transferFromWallet').value));
  const toW = state.wallets.find(w => w.id === parseInt(document.getElementById('transferToWallet').value));
  const group = document.getElementById('transferToSummaGroup');
  const toInput = document.getElementById('transferToSumma');
  const hint = document.getElementById('transferRateHint');
  if (!group || !toInput || !hint) return;

  document.getElementById('transferSummaLabel').textContent = fromW ? `O'tkazma miqdori (${fromW.currency}) *` : "O'tkazma miqdori *";
  const seq = ++_transferPreviewSeq;
  const differs = fromW && toW && fromW.currency !== toW.currency;
  group.style.display = differs ? '' : 'none';
  if (!differs) {
    toInput.value = '';
    hint.textContent = '';
    return;
  }

  document.getElementById('transferToSummaLabel').textContent = `Tushadigan miqdor (${toW.currency})`;
  const amount = readAmount('transferSumma') || 0;
  try {
    const q = `from=${encodeURIComponent(fromW.currency)}&to=${encodeURIComponent(toW.currency)}&amount=${amount > 0 ? amount : 1}`;
    const res = await fetch(`${API_BASE}/rates/convert/?${q}`);
    const data = await res.json().catch(() => ({}));
    if (seq !== _transferPreviewSeq) return; // foydalanuvchi shu orada boshqa narsa tanlagan
    if (!res.ok) {
      toInput.placeholder = 'Miqdorni kiriting';
      hint.textContent = "Kursni aniqlab bo'lmadi — tushadigan miqdorni qo'lda kiriting.";
      return;
    }
    const rateText = formatRateText(fromW.currency, toW.currency, Number(data.rate));
    if (amount > 0) {
      toInput.placeholder = `${formatNumber(data.result)} (avtomatik)`;
      hint.textContent = `Markaziy bank kursi: ${rateText}. Bo'sh qoldirilsa ${formatNumber(data.result)} ${toW.currency} yoziladi. Bank boshqa miqdor bergan bo'lsa, haqiqiysini kiriting.`;
    } else {
      toInput.placeholder = 'Avtomatik hisoblanadi';
      hint.textContent = `Markaziy bank kursi: ${rateText}`;
    }
    // Tahrirda hamyonlar o'zgarmasa server o'tkazma kunidagi kursni saqlaydi (serializers.py: _fill_to_summa)
    const old = _txEdit?.type === 'transfer' ? _txEdit.raw : null;
    if (old && old.from_wallet === fromW.id && old.to_wallet === toW.id) {
      toInput.placeholder = 'Eski kurs bo\'yicha';
      hint.textContent = `Bo'sh qoldirilsa o'tkazma kunidagi kurs saqlanadi: ${formatRateText(fromW.currency, toW.currency, Number(old.rate))}.`;
    }
  } catch (err) {
    if (seq === _transferPreviewSeq) hint.textContent = "Kursni aniqlab bo'lmadi — tushadigan miqdorni qo'lda kiriting.";
  }
}
document.getElementById('transferFromWallet')?.addEventListener('change', () => {
  syncTransferTargets();
  updateTransferCurrencyPreview();
});
document.getElementById('transferToWallet')?.addEventListener('change', updateTransferCurrencyPreview);
document.getElementById('transferSumma')?.addEventListener('input', () => {
  clearTimeout(updateTransferCurrencyPreview._t);
  updateTransferCurrencyPreview._t = setTimeout(updateTransferCurrencyPreview, 300);
});

// Qarz doim hamyonga bog'lanadi: valyutasi hamyonniki bo'ladi
function updateDebtCurrencyField() {
  const select = document.getElementById('debtWalletSelect');
  const hint = document.getElementById('debtWalletCurrencyHint');
  if (!select || !hint) return;
  const wallet = state.wallets.find(w => String(w.id) === select.value);
  hint.textContent = wallet ? `Qarz hamyon valyutasida yoziladi: ${wallet.currency}` : '';
  document.getElementById('debtSummaLabel').textContent = wallet ? `Miqdor (${wallet.currency}) *` : 'Miqdor *';
}
document.getElementById('debtWalletSelect')?.addEventListener('change', updateDebtCurrencyField);

onSubmitOnce('formRepayDebt', async (e) => {
  e.preventDefault();
  if (!activeRepayDebtId) return;

  const payload = {
    amount: readAmount('repayAmount'),
    wallet: parseInt(document.getElementById('repayWalletSelect').value)
  };

  try {
    const res = await fetch(`${API_BASE}/debts/${activeRepayDebtId}/repay/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Qarz to\'landi va hamyon yangilandi!');
      closeModal('modalRepayDebt');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarzni to\'lashda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// ==========================================
// DELETE HANDLERS
// ==========================================

async function deleteTransaction(type, id) {
  if (!(await confirmDelete("Ushbu amalni bekor qilib o'chirishni xohlaysizmi? Hamyon qoldig'i qaytariladi."))) {
    return;
  }

  const endpoint = TX_FORMS[type].api;

  try {
    const res = await fetch(`${API_BASE}/${endpoint}/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Amaliyot o\'chirildi va qoldiq qaytarildi', 'success', {
        action: { label: 'Qaytarish', onClick: () => restoreTransaction(type, id) },
      });
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'O\'chirishda xatolik yuz berdi (hamyonda qoldiq yetarli bo\'lmasligi mumkin)'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

// "Qaytarish" — o'chirilgan operatsiya qayta faol bo'ladi va balansga yana ta'sir qiladi (views.py: RestoreMixin)
async function restoreTransaction(type, id) {
  try {
    const res = await fetch(`${API_BASE}/${TX_FORMS[type].api}/${id}/restore/`, { method: 'POST' });
    if (res.ok) {
      showToast('Amaliyot qaytarildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Amaliyotni qaytarib bo\'lmadi'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

async function deleteDebt(id) {
  if (!(await confirmDelete('Qarz yozuvini o\'chirishni xohlaysizmi?'))) return;

  try {
    const res = await fetch(`${API_BASE}/debts/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Qarz o\'chirildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarzni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

async function deleteWallet(id) {
  if (!(await confirmDelete('Hamyonni o\'chirishni xohlaysizmi? Oldingi barcha amallar arxivlanadi.'))) return;

  try {
    const res = await fetch(`${API_BASE}/wallets/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Hamyon muvaffaqiyatli o\'chirildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Hamyonni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

async function deleteMember(id) {
  if (!(await confirmDelete('A\'zoni o\'chirishni xohlaysizmi?'))) return;

  try {
    const res = await fetch(`${API_BASE}/members/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('A\'zo o\'chirildi');
      await Promise.all([fetchMembers(), fetchRecurring()]);
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'A\'zoni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

// ==========================================
// TAKRORIY TO'LOVLAR
// ==========================================
// Server muddati kelganini o'zi yozadi (mainapp/recurring.py). Bu yerda — ro'yxat, qo'shish/tahrirlash va eslatmalar
const RECURRING_FREQ_LABELS = { daily: 'Har kuni', weekly: 'Har hafta', monthly: 'Har oy', yearly: 'Har yil' };

// 'YYYY-MM-DD' gacha necha kun (bugun — 0, o'tgan — manfiy)
function daysUntil(isoDate) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.round((new Date(isoDate + 'T00:00:00') - today) / 86400000);
}

async function fetchRecurring() {
  try {
    const res = await fetch(`${API_BASE}/recurring/`);
    if (res.ok) {
      const data = await res.json();
      state.recurring = data.results || data;
      renderRecurring();
      renderNotifications();
    }
  } catch (err) {
    console.error('Error fetching recurring payments:', err);
  }
}

function recurringCardHtml(r, preview = false) {
  const days = daysUntil(r.next_date);
  const when = days === 0 ? 'bugun' : days === 1 ? 'ertaga' : formatUzDate(r.next_date + 'T00:00:00');
  const sign = r.kind === 'income' ? '+' : '-';
  const status = r.last_error
    ? `<span class="debt-due-overdue" title="${escapeHtml(r.last_error)}">${icon('warning')} yozilmadi</span>`
    : `<span class="${days <= r.remind_days ? 'debt-due-soon' : 'debt-due-normal'}"><span>${escapeHtml(RECURRING_FREQ_LABELS[r.frequency])}</span> · <span>${escapeHtml(when)}</span></span>`;
  return `
      <div class="member-compact-card${preview ? '' : ' is-clickable'}"${preview ? '' : ` data-recurring-id="${r.id}" role="button" tabindex="0" title="Tahrirlash"`}>
        <div>
          <div style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${icon('repeat')} ${escapeHtml(r.name)}</div>
          <div style="font-size: 0.75rem;">${status}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <div class="recurring-amount ${r.kind}">${sign}${formatNumber(r.summa)} <span>${escapeHtml(r.wallet_currency)}</span></div>
          ${preview ? '' : `<button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="O'chirish" data-action="deleteRecurring" data-stop data-args="${actionArgs(r.id)}">${icon('trash')}</button>`}
        </div>
      </div>`;
}

function renderRecurring() {
  updateHomeListCount();
  // Bosh sahifada eng yaqin to'lov (sanasi bo'yicha birinchisi)
  const nearest = [...state.recurring].sort((a, b) => String(a.next_date).localeCompare(String(b.next_date)))[0];
  renderHomePreview('recurringPreview', nearest ? recurringCardHtml(nearest, true) : '');
  const container = document.getElementById('recurringList');
  if (!container) return;
  if (!state.recurring.length) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Ijara, kommunal, obuna yoki maosh kabi har oy takrorlanadigan to'lovlarni qo'shing — ular o'zi yoziladi</p>`;
    return;
  }
  container.innerHTML = state.recurring.map(r => recurringCardHtml(r)).join('');
}

// Eslatmalar: yozilmay qolgan (masalan pul yetmagan) va muddati yaqinlashganlar
function getRecurringAlerts() {
  return (state.recurring || [])
    .map(r => ({ r, days: daysUntil(r.next_date) }))
    .filter(({ r, days }) => r.last_error || (days >= 0 && days <= r.remind_days))
    .sort((a, b) => a.days - b.days);
}

function fillRecurringCategories(kind, selected) {
  const select = document.getElementById('recurringCategory');
  const list = kind === 'income' ? state.incomeCategories : state.expenseCategories;
  select.innerHTML = '<option value="" disabled selected>-- Tanlang --</option>'
    + list.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
  document.getElementById('recurringCategoryLabel').textContent = kind === 'income' ? 'Kirim manbayi *' : 'Chiqim turkumi *';
  document.getElementById('recurringMemberGroup').style.display = kind === 'expense' && state.members.length ? '' : 'none';
  if (selected) selectValueOrKeep('recurringCategory', selected.id, selected.name);
  if (select._csSync) select._csSync();
}

function updateRecurringSummaLabel() {
  const wallet = state.wallets.find(w => String(w.id) === document.getElementById('recurringWallet').value);
  document.getElementById('recurringSummaLabel').textContent = wallet ? `Miqdor (${wallet.currency}) *` : 'Miqdor *';
}

function openRecurringModal(id) {
  const form = document.getElementById('formRecurring');
  const r = id ? state.recurring.find(x => x.id === id) : null;
  form.reset();
  if (r) form.dataset.editId = r.id; else delete form.dataset.editId;
  const modal = document.getElementById('modalRecurring');
  modal.querySelector('[data-tx-title]').textContent = r ? "Doimiy to'lovni tahrirlash" : "Doimiy to'lov";

  const walletSel = document.getElementById('recurringWallet');
  walletSel.innerHTML = spendableWallets().map(w => `<option value="${w.id}">${escapeHtml(w.name)} (${escapeHtml(w.currency)})</option>`).join('');
  document.getElementById('recurringMember').innerHTML = '<option value="">-- O\'zim uchun --</option>'
    + state.members.map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`).join('');

  const kind = r ? r.kind : 'expense';
  document.getElementById('recurringKind').value = kind;
  fillRecurringCategories(kind, r && {
    id: kind === 'income' ? r.income_category : r.expense_category, name: r.category_name,
  });
  if (r) {
    document.getElementById('recurringName').value = r.name;
    document.getElementById('recurringSumma').value = r.summa;
    selectValueOrKeep('recurringWallet', r.wallet, r.wallet_name);
    selectValueOrKeep('recurringMember', r.member, r.member_name);
    document.getElementById('recurringFrequency').value = r.frequency;
    document.getElementById('recurringStart').value = r.start_date;
    document.getElementById('recurringEnd').value = r.end_date || '';
    document.getElementById('recurringRemind').value = r.remind_days;
  } else {
    document.getElementById('recurringStart').value = getCurrentDateLocal();
  }
  ['recurringKind', 'recurringFrequency', 'recurringWallet', 'recurringMember'].forEach(sid => {
    document.getElementById(sid)._csSync?.();
  });
  updateRecurringSummaLabel();
  openModal('modalRecurring');
}

document.getElementById('recurringKind')?.addEventListener('change', e => fillRecurringCategories(e.target.value));
document.getElementById('recurringWallet')?.addEventListener('change', updateRecurringSummaLabel);
document.getElementById('recurringList')?.addEventListener('click', e => {
  const card = e.target.closest('[data-recurring-id]');
  if (card) openRecurringModal(Number(card.dataset.recurringId));
});
document.getElementById('recurringList')?.addEventListener('keydown', e => {
  const card = e.target.closest('[data-recurring-id]');
  if (card && e.target === card && (e.key === 'Enter' || e.key === ' ')) {
    e.preventDefault();
    openRecurringModal(Number(card.dataset.recurringId));
  }
});

onSubmitOnce('formRecurring', async (e) => {
  const form = e.target;
  const kind = document.getElementById('recurringKind').value;
  const category = parseInt(document.getElementById('recurringCategory').value);
  if (!category) {
    showToast(kind === 'income' ? 'Kirim manbayini tanlang' : 'Chiqim turkumini tanlang', 'error');
    return;
  }
  const memberVal = document.getElementById('recurringMember').value;
  const payload = {
    kind,
    name: document.getElementById('recurringName').value.trim(),
    summa: readAmount('recurringSumma'),
    wallet: parseInt(document.getElementById('recurringWallet').value),
    [kind === 'income' ? 'income_category' : 'expense_category']: category,
    member: kind === 'expense' && memberVal ? parseInt(memberVal) : null,
    frequency: document.getElementById('recurringFrequency').value,
    start_date: document.getElementById('recurringStart').value,
    end_date: document.getElementById('recurringEnd').value || null,
    remind_days: parseInt(document.getElementById('recurringRemind').value) || 0,
  };
  const editId = form.dataset.editId;
  try {
    const res = await fetch(editId ? `${API_BASE}/recurring/${editId}/` : `${API_BASE}/recurring/`, {
      method: editId ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      showToast(editId ? "Doimiy to'lov o'zgartirildi" : "Doimiy to'lov qo'shildi");
      closeModal('modalRecurring');
      // Bugungi to'lov darhol yozilishi mumkin — balans va ro'yxatlar ham yangilansin
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, "Doimiy to'lovni saqlashda xatolik"), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

async function deleteRecurring(id) {
  if (!(await confirmDelete("Doimiy to'lov o'chirilsinmi? Avval yozilgan amallar saqlanib qoladi."))) return;
  try {
    const res = await fetch(`${API_BASE}/recurring/${id}/`, { method: 'DELETE' });
    if (res.ok) {
      showToast("Doimiy to'lov o'chirildi");
      await fetchRecurring();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, "O'chirishda xatolik"), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

// ==========================================
// JAMG'ARMA MAQSADLARI
// ==========================================
async function fetchGoals() {
  try {
    const res = await fetch(`${API_BASE}/goals/`);
    if (res.ok) {
      const data = await res.json();
      state.goals = data.results || data;
      renderGoals();
    }
  } catch (err) {
    console.error('Error fetching goals:', err);
  }
}

function goalCardHtml(g, preview = false) {
  const saved = Math.max(0, Number(g.saved));
  const target = Number(g.target);
  const pct = Math.min(100, Math.floor(saved / target * 100));
  const done = saved >= target;
  // Har bo'lak alohida <span>: i18n.js matnni butun bo'lak bo'yicha tarjima qiladi
  let note = done ? `${icon('check')} <span>Maqsadga yetildi</span>`
    : `<span>Yana ${formatNumber(target - saved)} ${escapeHtml(g.wallet_currency)}</span>`;
  if (!done && g.deadline) {
    const days = daysUntil(g.deadline);
    note += days < 0 ? ` · <span>muddat o'tgan</span>` : ` · <span>${days} kun qoldi</span>`;
  }
  const actions = preview ? '' : `
          <span class="goal-actions">
            ${done ? '' : `<button class="btn btn-subtle btn-xs" data-action="fundGoal" data-stop data-args="${actionArgs(g.id)}">+ Pul qo'shish</button>`}
            <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="O'chirish" data-action="deleteGoal" data-stop data-args="${actionArgs(g.id)}">${icon('trash')}</button>
          </span>`;
  return `
      <div class="goal-card${preview ? '' : ' is-clickable'}"${preview ? '' : ` data-goal-id="${g.id}" role="button" tabindex="0" title="Tahrirlash"`}>
        <div class="goal-head">
          <span class="goal-name">${icon('target')} ${escapeHtml(g.name)}</span>
          <span class="goal-sum">${formatNumber(saved)} / ${formatNumber(target)} <small>${escapeHtml(g.wallet_currency)}</small></span>
        </div>
        <div class="goal-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width: ${pct}%"></span></div>
        <div class="goal-foot">
          <span class="${done ? 'goal-done' : ''}"><span>${pct}%</span> · ${note}</span>${actions}
        </div>
      </div>`;
}

function renderGoals() {
  updateHomeListCount();
  renderHomePreview('goalsPreview', state.goals.length ? goalCardHtml(state.goals[0], true) : '');
  const container = document.getElementById('goalsList');
  if (!container) return;
  if (!state.goals.length) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Mashina, ta'til yoki uy uchun maqsad qo'ying — qancha yig'ilganini ko'rib borasiz</p>`;
    return;
  }
  container.innerHTML = state.goals.map(g => goalCardHtml(g)).join('');
}

function updateGoalTargetLabel() {
  const form = document.getElementById('formGoal');
  const g = form.dataset.editId ? state.goals.find(x => String(x.id) === form.dataset.editId) : null;
  const currency = g ? g.wallet_currency : document.getElementById('goalCurrency').value.trim().toUpperCase();
  document.getElementById('goalTargetLabel').textContent = currency ? `Maqsad miqdori (${currency}) *` : 'Maqsad miqdori *';
}

// Yangi maqsad: valyuta so'raladi (hamyon server tomonida ochiladi). Tahrir: hamyon faqat ko'rsatiladi
function openGoalModal(id) {
  const form = document.getElementById('formGoal');
  const g = id ? state.goals.find(x => x.id === id) : null;
  form.reset();
  if (g) form.dataset.editId = g.id; else delete form.dataset.editId;
  document.getElementById('modalGoal').querySelector('[data-tx-title]').textContent = g ? 'Maqsadni tahrirlash' : 'Yangi maqsad';
  const currencyInput = document.getElementById('goalCurrency');
  document.getElementById('goalCurrencyGroup').hidden = !!g;
  currencyInput.required = !g;
  document.getElementById('goalWalletInfo').hidden = !g;
  if (g) {
    document.getElementById('goalName').value = g.name;
    document.getElementById('goalWalletName').textContent = `${g.wallet_name} (${g.wallet_currency})`;
    document.getElementById('goalTarget').value = g.target;
    document.getElementById('goalDeadline').value = g.deadline || '';
  }
  updateGoalTargetLabel();
  openModal('modalGoal');
}

document.getElementById('goalCurrency')?.addEventListener('input', updateGoalTargetLabel);
document.getElementById('goalsList')?.addEventListener('click', e => {
  const card = e.target.closest('[data-goal-id]');
  if (card) openGoalModal(Number(card.dataset.goalId));
});
document.getElementById('goalsList')?.addEventListener('keydown', e => {
  const card = e.target.closest('[data-goal-id]');
  if (card && e.target === card && (e.key === 'Enter' || e.key === ' ')) {
    e.preventDefault();
    openGoalModal(Number(card.dataset.goalId));
  }
});

onSubmitOnce('formGoal', async (e) => {
  const editId = e.target.dataset.editId;
  const payload = {
    name: document.getElementById('goalName').value.trim(),
    target: readAmount('goalTarget'),
    deadline: document.getElementById('goalDeadline').value || null,
  };
  if (!editId) payload.currency = document.getElementById('goalCurrency').value.trim() || 'UZS';
  try {
    const res = await fetch(editId ? `${API_BASE}/goals/${editId}/` : `${API_BASE}/goals/`, {
      method: editId ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      showToast(editId ? "Maqsad o'zgartirildi" : "Maqsad qo'shildi");
      closeModal('modalGoal');
      await refreshAll();  // maqsad hamyoni ochildi yoki qayta nomlandi — hamyonlar ro'yxati ham yangilanadi
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Maqsadni saqlashda xatolik'), 'error');
    }
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// Maqsad hamyoni maqsad bilan birga o'chadi. Unda pul bo'lsa, avval qaysi hamyonga o'tkazilishi so'raladi
// (server O'tkazma yozadi, so'ng hamyonni o'chiradi). Eski maqsad oddiy hamyonga bog'langan — hamyonga tegilmaydi
async function deleteGoal(id) {
  const g = state.goals.find(x => x.id === id);
  if (!g) return;
  const saved = Number(g.saved) || 0;
  if (g.wallet_is_goal && saved > 0) {
    const targets = spendableWallets();
    if (!targets.length) {
      showToast("Maqsaddagi pulni o'tkazish uchun oddiy hamyon kerak — avval hamyon qo'shing", 'error');
      return;
    }
    const form = document.getElementById('formGoalDelete');
    form.dataset.goalId = g.id;
    document.getElementById('goalDeleteText').textContent =
      `«${g.name}» maqsadida ${formatMoney(saved, g.wallet_currency)} yig'ilgan. Pul tanlangan hamyonga o'tkaziladi, so'ng maqsad va uning hamyoni o'chadi.`;
    const select = document.getElementById('goalDeleteTarget');
    // Avval maqsad bilan bir xil valyutadagi hamyonlar: boshqa valyutaga Markaziy bank kursi bo'yicha o'giriladi
    const sorted = [...targets].sort((a, b) => (a.currency !== g.wallet_currency) - (b.currency !== g.wallet_currency));
    select.innerHTML = sorted.map(w => `<option value="${w.id}">${escapeHtml(w.name)} (${formatMoney(w.summa, w.currency)})</option>`).join('');
    select._csSync?.();
    openModal('modalGoalDelete');
    return;
  }
  const message = g.wallet_is_goal
    ? "Maqsad o'chirilsinmi? Uning hamyoni ham o'chadi."
    : "Maqsad o'chirilsinmi? Hamyon va undagi pul joyida qoladi.";
  if (!(await confirmDelete(message))) return;
  await sendGoalDelete(id);
}

async function sendGoalDelete(id, toWallet = null) {
  try {
    const res = await fetch(`${API_BASE}/goals/${id}/`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toWallet ? { to_wallet: toWallet } : {}),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(data.message || "Maqsad o'chirildi");
      await refreshAll();  // hamyon o'chdi va pul boshqa hamyonga o'tdi — qoldiqlar ham yangilanadi
      return true;
    }
    showToast(extractErrorMessage(data, "O'chirishda xatolik"), 'error');
  } catch (error) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
  return false;
}

onSubmitOnce('formGoalDelete', async (e) => {
  const id = Number(e.target.dataset.goalId);
  const toWallet = parseInt(document.getElementById('goalDeleteTarget').value);
  if (await sendGoalDelete(id, toWallet)) closeModal('modalGoalDelete');
});

// "Pul qo'shish" — O'tkazma oynasi maqsad hamyoniga yo'naltirilgan holda ochiladi. "Qaysi hamyonga" qulflanadi:
// pul faqat shu maqsad hamyoniga tushadi (oyna yopilganda closeModal -> unlockTransferTarget)
function fundGoal(id) {
  const g = state.goals.find(x => x.id === id);
  if (!g) return;
  const sources = spendableWallets().filter(w => w.id !== g.wallet);
  if (!sources.length) {
    showToast("Pul qo'shish uchun oddiy hamyon kerak: pul o'sha hamyondan maqsad hamyoniga o'tkaziladi", 'error');
    return;
  }
  const to = document.getElementById('transferToWallet');
  const from = document.getElementById('transferFromWallet');
  if (!sources.some(w => String(w.id) === from.value)) from.value = String(sources[0].id);
  syncTransferTargets();
  to.value = String(g.wallet);
  to.disabled = true;
  [to, from].forEach(el => el._csSync?.());
  document.getElementById('transferDescription').value = `Maqsad: ${g.name}`;
  openModal('modalTransfer');
}

function unlockTransferTarget() {
  const to = document.getElementById('transferToWallet');
  if (!to?.disabled) return;
  to.disabled = false;
  // Bekor qilingan «Pul qo'shish»: maqsad hamyoni va «Maqsad: …» izohi keyingi oddiy o'tkazmaga o'tib qolmasin
  document.getElementById('formAddTransfer')?.reset();
  syncTransferTargets();
  [to, document.getElementById('transferFromWallet')].forEach(el => el?._csSync?.());
}

// Helper
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}


// ==========================================
// AUTHENTICATION ENGINE
// ==========================================

// Chiqishdan keyin oldingi foydalanuvchining ma'lumotlari (ochiq oynalar va bo'lim sahifalari, ro'yxatlar,
// tanlagichlar) ekranda ham, sahifa xotirasida ham qolmasligi uchun sahifa toza holda qayta yuklanadi.
// Xabar qayta yuklangandan keyin ko'rsatiladi
const FLASH_KEY = 'moliyaFlash';

function reloadSignedOut(message, type = 'success') {
  try {
    sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message, type }));
  } catch (e) { /* xabarsiz qayta yuklanadi */ }
  location.reload();
}

function showFlashMessage() {
  try {
    const raw = sessionStorage.getItem(FLASH_KEY);
    if (!raw) return;
    sessionStorage.removeItem(FLASH_KEY);
    const { message, type } = JSON.parse(raw);
    if (message) showToast(message, type);
  } catch (e) { /* e'tiborsiz */ }
}

async function checkAuth() {
  const authSection = document.getElementById('authSection');
  const mainApp = document.getElementById('mainApp');
  const userProfileNav = document.getElementById('userProfileNav');

  let data = null;
  try {
    const res = await fetch(`${API_BASE}/auth/me/`);
    if (res.ok) data = await res.json();
  } catch (err) {
    console.error('Auth check error:', err);
  }

  if (state.currentUser && !(data && data.authenticated)) {
    // Server javob bermadi (tarmoq uzildi) — sessiya hali amalda bo'lishi mumkin, foydalanuvchi chiqarilmaydi
    if (!data) return false;
    reloadSignedOut('Sessiya tugadi — qaytadan kiring', 'error');
    return false;
  }

  if (data && data.authenticated) {
    state.currentUser = data.user;
    state.currentUserId = data.user.id;
    try { localStorage.removeItem(`moliyaNotifs:${data.user.id}`); } catch (e) { /* e'tiborsiz */ }

    // Show main app, hide auth screen
    document.body.classList.remove('is-auth');
    if (authSection) authSection.style.display = 'none';
    if (mainApp) mainApp.style.display = 'block';
    if (userProfileNav) userProfileNav.style.display = 'flex';
    const navSections = document.getElementById('navSections');
    if (navSections) navSections.style.display = 'flex';
    // Bo'limlar kapsulasi chiqqach navbar balandlashadi — ro'yxat sahifalari uning ostidan to'g'ri boshlansin
    syncNavbarHeight();
    // Brend endi bo'limlar kapsulasida ("Moliya") — alohida logotip takrorlanmasin
    const brandLogo = document.getElementById('brandLogo');
    if (brandLogo) brandLogo.style.display = 'none';
    const notifWrap = document.getElementById('notifWrap');
    if (notifWrap) notifWrap.style.display = 'block';
    renderUserNav();
    // Ovozli yordamchi (voice.js) — faqat kirgan foydalanuvchiga: «Salom Moliya» yoqilgan bo'lsa fonda tinglaydi
    window.moliyaVoice?.start();
    setAssistantFab(true);
    startSupportUnreadPolling(data.user.support_unread);
    fetchNotices();

    refreshAll();
    return true;
  }

  // Not authenticated: Show login screen, hide main app
  state.currentUser = null;
  state.currentUserId = null;
  window.moliyaVoice?.stop();
  setAssistantFab(false);
  stopSupportUnreadPolling();
  _setNotifPanel(false);

  document.body.classList.add('is-auth');
  if (authSection) authSection.style.display = 'flex';
  if (mainApp) mainApp.style.display = 'none';
  if (userProfileNav) userProfileNav.style.display = 'none';
  const navSectionsEl = document.getElementById('navSections');
  if (navSectionsEl) navSectionsEl.style.display = 'none';
  const brandLogoEl = document.getElementById('brandLogo');
  if (brandLogoEl) brandLogoEl.style.display = '';
  const notifWrapEl = document.getElementById('notifWrap');
  if (notifWrapEl) notifWrapEl.style.display = 'none';

  state.summary = {};
  state.wallets = [];
  state.expenses = [];
  state.incomes = [];
  state.transfers = [];
  state.debts = [];
  renderSummary();
  renderWallets();
  renderTransactions();
  renderDebts();

  return false;
}

// Auth Tabs Switcher
document.getElementById('authTabLogin')?.addEventListener('click', () => {
  document.getElementById('authTabLogin').classList.add('active');
  document.getElementById('authTabRegister').classList.remove('active');
  document.getElementById('formLoginMain').style.display = 'flex';
  document.getElementById('formRegisterMain').style.display = 'none';
  const title = document.getElementById('authScreenTitle');
  if (title) title.textContent = 'Moliyaga xush kelibsiz';
});

document.getElementById('authTabRegister')?.addEventListener('click', () => {
  document.getElementById('authTabRegister').classList.add('active');
  document.getElementById('authTabLogin').classList.remove('active');
  document.getElementById('formLoginMain').style.display = 'none';
  document.getElementById('formRegisterMain').style.display = 'flex';
  const title = document.getElementById('authScreenTitle');
  if (title) title.textContent = 'Yangi Hisob Ochish';
});

// ==========================================
// PAROLNI UNUTDIM — emailga kod yuborish va yangi parol o'rnatish
// ==========================================

// 1 — login/email kiritib kod so'rash, 2 — kodni tekshirish, 3 — yangi parol o'rnatish
let forgotStep = 1;

const FORGOT_STEPS = {
  1: {
    button: 'Kod yuborish',
    intro: "Foydalanuvchi nomingiz yoki elektron pochtangizni kiriting — hisobga ulangan elektron pochtaga 6 xonali tiklash kodi yuboramiz."
  },
  2: {
    button: 'Kodni tekshirish',
    intro: "Elektron pochtangizga 6 xonali kod yuborildi (spam papkasini ham tekshiring). Kod 15 daqiqa amal qiladi."
  },
  3: {
    button: 'Parolni yangilash',
    intro: "Kod tasdiqlandi. Endi yangi parol o'rnating."
  }
};

function setForgotStep(step) {
  forgotStep = step;
  document.getElementById('forgotStepCode').hidden = step !== 2;
  document.getElementById('forgotStepPassword').hidden = step !== 3;
  document.getElementById('btnForgotResend').hidden = step !== 2;
  document.getElementById('forgotUsername').readOnly = step !== 1;
  document.getElementById('btnForgotSubmit').textContent = FORGOT_STEPS[step].button;
  document.getElementById('forgotIntro').textContent = FORGOT_STEPS[step].intro;
}

// Kod ko'chirib qo'yilganda probel/defis qo'shilib qolishi mumkin — faqat raqamlarni olamiz
function getForgotCode() {
  return document.getElementById('forgotCode').value.replace(/\D/g, '');
}

function showForgotPassword(show) {
  const loginForm = document.getElementById('formLoginMain');
  const forgotForm = document.getElementById('formForgotPassword');
  const tabs = document.querySelector('.auth-tabs');
  const title = document.getElementById('authScreenTitle');

  loginForm.style.display = show ? 'none' : 'flex';
  forgotForm.style.display = show ? 'flex' : 'none';
  if (tabs) tabs.style.display = show ? 'none' : '';
  if (title) title.textContent = show ? 'Parolni tiklash' : 'Moliyaga xush kelibsiz';

  if (show) {
    forgotForm.reset();
    document.getElementById('forgotUsername').value = document.getElementById('loginUsername').value.trim();
    setForgotStep(1);
    document.getElementById('forgotUsername').focus();
  }
}

async function requestResetCode() {
  const username = document.getElementById('forgotUsername').value.trim();
  if (!username) {
    showToast('Foydalanuvchi nomi yoki elektron pochtani kiriting', 'error');
    return false;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/password-reset/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(data.message || 'Kod yuborildi');
      return true;
    }
    showToast(extractErrorMessage(data, 'Kod yuborishda xatolik'), 'error');
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
  return false;
}

document.getElementById('btnForgotPassword')?.addEventListener('click', () => showForgotPassword(true));
document.getElementById('btnForgotBack')?.addEventListener('click', () => showForgotPassword(false));

document.getElementById('btnForgotResend')?.addEventListener('click', async () => {
  if (await requestResetCode()) document.getElementById('forgotCode').value = '';
});

document.getElementById('forgotCode')?.addEventListener('input', (e) => {
  e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
  // 6 ta raqam kiritilishi bilan kod avtomatik tekshiriladi
  if (forgotStep === 2 && e.target.value.length === 6 && !document.getElementById('btnForgotSubmit').disabled) {
    document.getElementById('formForgotPassword').requestSubmit();
  }
});

document.getElementById('formForgotPassword')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById('btnForgotSubmit');
  submitBtn.disabled = true;

  try {
    if (forgotStep === 1) {
      if (await requestResetCode()) {
        setForgotStep(2);
        document.getElementById('forgotCode').focus();
      }
      return;
    }

    const username = document.getElementById('forgotUsername').value.trim();
    const code = getForgotCode();

    if (forgotStep === 2) {
      if (code.length !== 6) {
        showToast(`Kod 6 xonali bo'lishi kerak — siz ${code.length} ta raqam kiritdingiz`, 'error');
        return;
      }
      const res = await fetch(`${API_BASE}/auth/password-reset/verify/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, code })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setForgotStep(3);
        document.getElementById('forgotNewPassword').focus();
      } else {
        showToast(extractErrorMessage(data, 'Kod noto\'g\'ri'), 'error');
        document.getElementById('forgotCode').select();
      }
      return;
    }

    const newPassword = document.getElementById('forgotNewPassword').value.trim();
    const newPassword2 = document.getElementById('forgotNewPassword2').value.trim();

    if (newPassword.length < 8) {
      showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak", 'error');
      return;
    }
    if (newPassword !== newPassword2) {
      showToast('Yangi parollar bir-biriga mos kelmadi', 'error');
      return;
    }

    const res = await fetch(`${API_BASE}/auth/password-reset/confirm/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, code, new_password: newPassword })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(data.message || 'Parol yangilandi');
      showForgotPassword(false);
      document.getElementById('loginUsername').value = username;
      document.getElementById('loginPassword').value = '';
      document.getElementById('loginPassword').focus();
    } else {
      showToast(extractErrorMessage(data, 'Parolni tiklashda xatolik'), 'error');
      // Kod shu orada eskirgan bo'lsa — kod kiritish bosqichiga qaytamiz
      if (data.code) {
        setForgotStep(2);
        document.getElementById('forgotCode').value = '';
        document.getElementById('forgotCode').focus();
      }
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  } finally {
    submitBtn.disabled = false;
  }
});

// Login Form Submit (Main Auth Screen)
onSubmitOnce('formLoginMain', async (e) => {
  e.preventDefault();
  const usernameInput = document.getElementById('loginUsername');
  const passwordInput = document.getElementById('loginPassword');

  const payload = {
    username: usernameInput.value.trim(),
    password: passwordInput.value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (res.ok && data.two_factor) {
      // Parol to'g'ri, lekin ikki bosqichli kirish yoqilgan — emailga kelgan kod so'raladi
      showLoginCode(data);
    } else if (res.ok) {
      showToast(`Xush kelibsiz, ${data.user.name || data.user.username}!`);
      e.target.reset();
      await checkAuth();
    } else {
      showToast(extractErrorMessage(data, 'Login yoki parol noto\'g\'ri'), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// ── Sozlamalar → Qurilmalar: ikki bosqichli kirishni yoqish / o'chirish ──────────
// idle — holat va tugma; password — joriy parol so'raladi; code — emailga kelgan kod (faqat yoqishda)
let _twoFactor = { mode: 'idle', target: false, token: null };

function setTwoFactorMode(mode) {
  _twoFactor.mode = mode;
  const enabled = !!state.currentUser?.two_factor_enabled;
  document.getElementById('twoFactorStatus').textContent = enabled
    ? "Yoqilgan. Yangi qurilmadan kirishda elektron pochtangizga kod yuboriladi."
    : "O'chiq. Yoqilsa, yangi qurilmadan kirishda parol bilan birga elektron pochtaga kelgan kod ham so'raladi.";
  document.getElementById('twoFactorBox').classList.toggle('is-on', enabled);
  const toggle = document.getElementById('btnTwoFactorToggle');
  toggle.textContent = enabled ? "O'chirish" : 'Yoqish';
  toggle.hidden = mode !== 'idle';
  document.getElementById('twoFactorStep').hidden = mode === 'idle';
  document.getElementById('twoFactorPasswordGroup').hidden = mode !== 'password';
  document.getElementById('twoFactorCodeGroup').hidden = mode !== 'code';
  document.getElementById('btnTwoFactorNext').textContent = mode === 'code' ? 'Tasdiqlash' : 'Davom etish';
  if (mode === 'idle') {
    document.getElementById('twoFactorPassword').value = '';
    document.getElementById('twoFactorCode').value = '';
    _twoFactor.token = null;
  }
  if (mode === 'password') document.getElementById('twoFactorPassword').focus();
  if (mode === 'code') document.getElementById('twoFactorCode').focus();
}

document.getElementById('btnTwoFactorToggle')?.addEventListener('click', () => {
  _twoFactor.target = !state.currentUser?.two_factor_enabled;
  if (_twoFactor.target && !state.currentUser?.email) {
    showToast("Avval Profil bo'limida elektron pochta kiriting — kod o'sha elektron pochtaga keladi", 'error');
    return;
  }
  setTwoFactorMode('password');
});
document.getElementById('btnTwoFactorCancel')?.addEventListener('click', () => setTwoFactorMode('idle'));

async function submitTwoFactor() {
  const btn = document.getElementById('btnTwoFactorNext');
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    let res;
    if (_twoFactor.mode === 'password') {
      res = await fetch(`${API_BASE}/auth/two-factor/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: _twoFactor.target, password: document.getElementById('twoFactorPassword').value.trim() }),
      });
    } else {
      res = await fetch(`${API_BASE}/auth/two-factor/confirm/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: _twoFactor.token, code: document.getElementById('twoFactorCode').value.replace(/\D/g, '') }),
      });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showToast(extractErrorMessage(data, 'Xatolik yuz berdi'), 'error');
      return;
    }
    if (data.token) {
      // Yoqish: parol to'g'ri — endi emailga kelgan kod bilan tasdiqlanadi
      _twoFactor.token = data.token;
      document.getElementById('twoFactorCodeLabel').textContent = `${data.email} ga kelgan kod *`;
      setTwoFactorMode('code');
      return;
    }
    state.currentUser = data.user;
    showToast(data.message);
    setTwoFactorMode('idle');
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  } finally {
    btn.disabled = false;
  }
}
document.getElementById('btnTwoFactorNext')?.addEventListener('click', submitTwoFactor);
// Maydonlar Qurilmalar formasi ichida: Enter formani yubormasin, shu qadamni bajarsin
['twoFactorPassword', 'twoFactorCode'].forEach(id => {
  document.getElementById(id)?.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submitTwoFactor();
    }
  });
});

// ── Ikki bosqichli kirish: kod qadami ──────────
let _loginCodeToken = null;

function showLoginCode(data) {
  const show = !!data;
  _loginCodeToken = show ? data.token : null;
  document.getElementById('formLoginMain').style.display = show ? 'none' : 'flex';
  document.getElementById('formLoginCode').style.display = show ? 'flex' : 'none';
  const tabs = document.querySelector('.auth-tabs');
  if (tabs) tabs.style.display = show ? 'none' : '';
  const title = document.getElementById('authScreenTitle');
  if (title) title.textContent = show ? 'Kirishni tasdiqlash' : 'Moliyaga xush kelibsiz';
  document.getElementById('formLoginCode').reset();
  if (show) {
    document.getElementById('loginCodeIntro').textContent =
      `Kod ${data.email} manziliga yuborildi (spam papkasini ham tekshiring). Kod 10 daqiqa amal qiladi.`;
    document.getElementById('loginCode').focus();
  } else {
    document.getElementById('formLoginMain').reset();
  }
}

document.getElementById('btnLoginCodeBack')?.addEventListener('click', () => showLoginCode(null));

onSubmitOnce('formLoginCode', async () => {
  // Ko'chirib qo'yilganda probel/defis qo'shilib qolishi mumkin — faqat raqamlar
  const code = document.getElementById('loginCode').value.replace(/\D/g, '');
  if (code.length !== 6) {
    showToast('Elektron pochtaga kelgan 6 xonali kodni kiriting', 'error');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/login/verify/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: _loginCodeToken, code }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(`Xush kelibsiz, ${data.user.name || data.user.username}!`);
      showLoginCode(null);
      await checkAuth();
    } else {
      showToast(extractErrorMessage(data, "Kod noto'g'ri"), 'error');
      document.getElementById('loginCode').select();
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// Register Form Submit (Main Auth Screen)
onSubmitOnce('formRegisterMain', async (e) => {
  e.preventDefault();
  const payload = {
    username: document.getElementById('regUsername').value.trim(),
    password: document.getElementById('regPassword').value.trim(),
    email: document.getElementById('regEmail').value.trim(),
    first_name: document.getElementById('regFirstName').value.trim(),
    phone: document.getElementById('regPhone').value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(`Ro'yxatdan muvaffaqiyatli o'tdingiz, ${data.user.name || data.user.username}!`);
      e.target.reset();
      await checkAuth();
    } else {
      showToast(extractErrorMessage(data, 'Ro\'yxatdan o\'tishda xatolik yuz berdi'), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// ==========================================
// SOZLAMALAR — profil va parolni o'zgartirish
// ==========================================

function renderUserNav() {
  const user = state.currentUser;
  if (!user) return;
  const display = user.first_name || user.name || user.username;  // navbarda faqat ism (familiya qo'shilmaydi)
  const userName = document.getElementById('userName');
  const userAvatar = document.getElementById('userAvatar');
  if (userName) userName.textContent = display;
  if (userAvatar) userAvatar.textContent = display[0].toUpperCase();
  // Admin panel tugmasi: server faqat ruxsati bor foydalanuvchiga panel_url beradi
  const panelBtn = document.getElementById('btnPanel');
  if (panelBtn) {
    panelBtn.href = user.panel_url || '#';
    panelBtn.style.display = user.panel_url ? 'inline-flex' : 'none';
  }
}

// Ro'yxatdagi bo'lim nomi — i18n allaqachon tarjima qilgan matn, sarlavhaga shundayligicha ko'chiriladi
function settingsMenuLabel(tab) {
  return document.querySelector(`#settingsMenu [data-settings-tab="${tab}"] .help-row-text`)?.textContent || '';
}

// tab bo'sh bo'lsa — bo'limlar ro'yxati, aks holda o'sha bo'lim ekrani (tepasida "Orqaga")
function switchSettingsTab(tab) {
  document.getElementById('settingsMenu').hidden = !!tab;
  document.getElementById('settingsSubHead').hidden = !tab;
  document.querySelector('.settings-panels').hidden = !tab;
  document.querySelectorAll('[data-settings-panel]').forEach(panel => {
    panel.hidden = panel.dataset.settingsPanel !== tab;
  });
  if (!tab) {
    stopSupportPolling();
    // Ro'yxatga qaytilganda yarim qolgan tahrir va parol maydonlari tashlab yuboriladi
    if (state.currentUser) fillProfileForm(state.currentUser);
    setProfileMode('view');
    document.getElementById('formSettingsPassword').reset();
    return;
  }
  document.getElementById('settingsSubTitle').textContent = settingsMenuLabel(tab);
  if (tab === 'devices') {
    loadDevices();
    setTwoFactorMode('idle');
  }
  if (tab === 'help') showHelpTopics();
  if (tab === 'voice') window.moliyaVoice?.renderSettings();
  if (tab === 'assistant') {
    setAssistantDock(false);  // chat elementlari Sozlamalarga qaytadi
    openAssistant();
  }
  if (tab === 'support') openSupport();
  else stopSupportPolling();
}

// ==========================================
// MA'LUMOTNOMA (Sozlamalar → Ma'lumotnoma)
// ==========================================
// Har mavzu — savol-javoblar ro'yxati. Javobdagi har qator (\n) alohida xatboshi bo'lib chiqadi.
// Qoidalar server tekshiruvlari bilan bir xil yozilgan (views.py / serializers.py) — ular o'zgarsa bu yer ham yangilansin.
// Moliya yordamchisi shu savol-javoblarning nusxasiga tayanadi (mainapp/assistant_knowledge.md) — mavzu o'zgarsa uni ham yangilang
const HELP_TOPICS = [
  { id: 'start', icon: 'person', title: "Ro'yxatdan o'tish va kirish", items: [
    ["Qanday qilib ro'yxatdan o'tish mumkin?",
     "Kirish oynasida «Ro'yxatdan o'tish» bo'limini tanlang, foydalanuvchi nomi (login) va kamida 8 belgili parol kiriting.\nRo'yxatdan o'tgach ilova darhol ochiladi — birinchi hamyoningizni qo'shishdan boshlang."],
    ["Parolimni unutdim. Nima qilaman?",
     "Kirish oynasida «Parolni unutdingizmi?» tugmasini bosing va foydalanuvchi nomingiz yoki elektron pochtangizni kiriting. Hisobga ulangan elektron pochtaga 6 xonali kod yuboriladi — kodni va yangi parolni kiriting.\nKod faqat hisobda elektron pochta bo'lsa keladi. Shuning uchun elektron pochtani oldindan Sozlamalar → Profil bo'limida kiritib qo'ying. Xat «Spam» papkasiga tushib qolishi mumkin."],
    ["Profil ma'lumotlarini qanday o'zgartiraman?",
     "Sozlamalar → Profil bo'limida «Tahrirlash» tugmasini bosing. Ism, familiya, login, elektron pochta va telefonni o'zgartirib «Saqlash» ni bosing.\nElektron pochta parolni tiklash uchun ishlatilgani sababli uni o'zgartirishda joriy parol so'raladi.\nIkki bosqichli himoya yoqilgan bo'lsa, yangi elektron pochta unga kelgan kod bilan tasdiqlanadi — kod kiritilmaguncha eski elektron pochta saqlanib turadi."],
  ]},
  { id: 'home', icon: 'mobile', title: 'Bosh sahifa', items: [
    ["Bosh sahifadagi ma'lumotlarni qanday yangilayman?",
     "Bosh sahifa eng tepada turganda: telefon yoki planshetda barmoq bilan pastga torting, kompyuterda sichqoncha g'ildiragi yoki touchpad bilan yana yuqoriga aylantiring. Ilova belgisi chiqadi — halqasi to'lganda qo'yib yuboring: qoldiq, hamyonlar va amallar qayta yuklanadi. Yoki navbardagi «Moliya» tugmasini bosing — bosh sahifa eng tepaga chiqadi va ma'lumotlar yangilanadi."],
    ["Nega «Hamyonlar» bo'limida hamma hamyonlar ko'rinmaydi?",
     "Bosh sahifa ixcham bo'lishi uchun bu bo'limda faqat 2 ta hamyon turadi. Hammasini ko'rish uchun «Hamyonlar ›» sarlavhasini bosing. Har bir hamyon qoldig'i «Umumiy qoldiq» kartasida ham ko'rinadi."],
    ["Doimiy to'lovlar, maqsadlar va a'zolar ro'yxati qayerda?",
     "Bosh sahifada bu bo'limlarning faqat nomi turadi. Ro'yxatni ko'rish uchun bo'lim nomini bosing — u alohida sahifada ochiladi. Yangi yozuvni nom yonidagi «+» tugmasi bilan darhol qo'shish mumkin."],
    ["Ilova telefon va planshetda ishlaydimi?",
     "Ha. Ilova brauzerda ochiladi va ekran o'lchamiga o'zi moslashadi: telefonda ixcham, planshet va kompyuterda kengroq ko'rinadi. Alohida o'rnatish shart emas."],
    ["Moliya yordamchisi qayerda?",
     "Har sahifada pastki o'ng burchakdagi dumaloq tugmani bosing — Moliya yordamchisi oynasi ochiladi. Ilovadan qanday foydalanish bo'yicha savolingizni yozing. Oyna ochiq turganda ilovaning boshqa joylaridan ham foydalanish mumkin — u yopilmaydi. Yopish uchun oynadagi × ni yoki dumaloq tugmani yana bosing; suhbat Sozlamalar → Moliya yordamchisi bo'limida ham davom etadi."],
    ["Adminga qanday yozaman?",
     "Sozlamalar → Yordam bo'limida xabaringizni yozib yuboring. Admin javob berganda navbardagi qo'ng'iroqchada «Admin javob berdi» xabari chiqadi, o'qilmagan xabarlar soni Yordam bo'limi yonida ham ko'rinadi.\nIlovadan foydalanish bo'yicha darhol javob kerak bo'lsa, Moliya yordamchisidan so'rang."],
    ["Admin xabarlari qayerda ko'rinadi?",
     "Navbardagi qo'ng'iroqcha belgisini bosing — «Xabarlar» ro'yxatida admin yuborgan xabarlar eng tepada, yashil fonda va «Admin» belgisi bilan turadi. Barcha foydalanuvchilarga yuborilganida «Hammaga» deb yoziladi. Yangi xabar qo'ng'iroqchada son bilan bilinadi va ro'yxatni ochganingizda o'qilgan hisoblanadi; o'qilgan xabar 30 kun ko'rinib turadi."],
  ]},
  { id: 'wallets', icon: 'wallet', title: 'Hamyonlar', items: [
    ['Hamyon nima?',
     "Hamyon — pulingiz turgan har bir joy: naqd pul, bank kartasi, seyf va hokazo. Har bir kirim, chiqim va qarz qaysidir hamyonga yoziladi, shuning uchun avval kamida bitta hamyon oching."],
    ["Hamyonni qanday qo'shaman?",
     "Bosh sahifadagi «Hamyonlar» bo'limida qo'shish tugmasini bosing. Nom, hozirgi mablag' (hozir unda qancha pul borligi) va valyutani tanlang."],
    ["Hamyon qoldig'ini qo'lda o'zgartirsa bo'ladimi?",
     "Ha. Hamyon sahifasida «Tahrirlash» ni bosing va «Hamyondagi pul» maydoniga to'g'ri summani yozing. Pul shu summaga almashtiriladi, lekin kirim yoki chiqim sifatida yozilmaydi — shuning uchun tarixdagi amallar yig'indisi qoldiqqa mos kelmasligi mumkin. Pul qayerdan kelib, qayerga ketgani ko'rinishi kerak bo'lsa, farqni Kirim yoki Chiqim sifatida yozing."],
    ['Hamyon valyutasini almashtirsa bo\'ladimi?',
     "Faqat hamyonda hali birorta amal bo'lmasa. Amallar bo'lsa, boshqa valyutada yangi hamyon oching va pulni O'tkazma orqali o'tkazing."],
    ["Hamyonni qanday o'chiraman?",
     "Hamyon yonidagi o'chirish tugmasini bosing. O'chirish uchun hamyon qoldig'i 0 bo'lishi va unga to'lanmagan qarz bog'lanmagan bo'lishi kerak. Pul qolgan bo'lsa, avval uni O'tkazma orqali boshqa hamyonga o'tkazing.\nMaqsad hamyoni bu yerda o'chirilmaydi — uni Maqsadlar bo'limida maqsad bilan birga o'chiring."],
    ['Qoldiqni qanday yashiraman?',
     "Bosh sahifadagi qoldiq yonidagi ko'z belgisini bosing. Miqdor, hamyon nomlari va valyutalar xiralashadi. Qayta bosilsa ko'rinadi. Tanlov shu brauzerda eslab qolinadi."],
  ]},
  { id: 'income', icon: 'income', title: 'Kirim (daromad)', items: [
    ['Kirimni qanday yozaman?',
     "Bosh sahifada «Kirim» tugmasini bosing. Miqdor, pul tushgan hamyon va kirim manbayini (masalan, Maosh) tanlang. Sana va izoh ixtiyoriy.\nSaqlangach miqdor tanlangan hamyon qoldig'iga qo'shiladi."],
    ["Ro'yxatda kerakli manba yo'q bo'lsa-chi?",
     "Manbalar ro'yxatidan «Boshqa (o'zingiz yozing...)» ni tanlang va yangi nom yozing — u keyingi safar ro'yxatda turadi. Turkumlarni oldindan «Turkumlarni sozlash» oynasida ham qo'shish mumkin."],
    ["Barcha kirimlarni qayerdan ko'raman?",
     "Navbardagi «Kirim» bo'limini bosing. U yerda kirimlar sana bo'yicha ro'yxatlangan, davr va valyuta bo'yicha filtrlash mumkin."],
  ]},
  { id: 'expense', icon: 'expense', title: 'Chiqim (xarajat)', items: [
    ['Chiqimni qanday yozaman?',
     "Bosh sahifada «Chiqim» tugmasini bosing. Miqdor, pul chiqqan hamyon va turkumni (nimaga sarflandi) tanlang. Sana, «Kimga?» va izoh ixtiyoriy."],
    ["«Hamyonda mablag' yetarli emas» xatosi chiqdi. Nega?",
     "Chiqim miqdori tanlangan hamyondagi puldan oshib ketdi. Boshqa hamyonni tanlang yoki avval shu hamyonga Kirim yoki O'tkazma qiling. Hamyon qoldig'i manfiyga tushmaydi."],
    ["«Kimga?» maydoni nima uchun?",
     "Pul kimga sarflanganini belgilash uchun: masalan, ukangiz yoki akangizning oilasi. Ro'yxatga odam yoki oilani «A'zolar» bo'limida qo'shasiz. Bo'sh qoldirilsa — o'zingiz uchun hisoblanadi."],
  ]},
  { id: 'transfer', icon: 'transfer', title: "O'tkazma", items: [
    ["O'tkazma nima?",
     "Pulni bir hamyondan boshqasiga o'tkazish: masalan, kartadan naqd pul yechish. Umumiy qoldiq o'zgarmaydi, shuning uchun o'tkazma kirim yoki chiqim hisobiga kirmaydi."],
    ["Hamyonlar har xil valyutada bo'lsa-chi?",
     "«Tushadigan miqdor» kurs bo'yicha avtomatik hisoblanadi. Agar bank yoki ayirboshlash shoxobchasi boshqa kurs bergan bo'lsa, haqiqatda tushgan miqdorni o'zingiz yozing."],
  ]},
  { id: 'debts', icon: 'ledger', title: 'Qarzlar', items: [
    ['Qarzni qanday yozaman?',
     "«Qarz» tugmasini bosing, shaxs yoki tashkilot nomini, qarz turini, miqdorni va bog'langan hamyonni tanlang. Qaytarish muddati ixtiyoriy."],
    ["«Qarz berdim» va «Qarz oldim» farqi nima?",
     "«Qarz berdim» — siz birovga pul berdingiz: miqdor hamyoningizdan yechiladi va sizga qaytarilishi kutiladi.\n«Qarz oldim» — siz birovdan pul oldingiz: miqdor hamyoningizga qo'shiladi va uni qaytarishingiz kerak."],
    ["Qarzni qisman qaytarsa bo'ladimi?",
     "Ha. Qarzlar daftarida qarz yonidagi «To'lash» tugmasini bosing, to'langan miqdorni va hamyonni tanlang. Qolgan miqdor avtomatik kamayadi, to'liq to'langanda qarz yopiladi.\nTo'lov qolgan qarzdan ko'p bo'lishi mumkin emas."],
    ["Qarz boshqa valyutadagi hamyon orqali to'lansa-chi?",
     "Hamyonga kurs bo'yicha hisoblangan miqdor yoziladi. Kurs vaqtincha aniqlanmasa, qarz valyutasidagi hamyonni tanlang yoki keyinroq urinib ko'ring."],
    ["Qarzni o'chirsam nima bo'ladi?",
     "Qarzning to'lanmagan qismi hamyonga qaytariladi: «Qarz berdim» bo'lsa hamyonga qo'shiladi, «Qarz oldim» bo'lsa hamyondan yechiladi."],
  ]},
  { id: 'operations', icon: 'receipt', title: 'Amallarni tahrirlash va o\'chirish', items: [
    ["Xato yozilgan amalni qanday tuzataman?",
     "Kirim yoki Chiqim ro'yxatida amalni bosing — tafsilotlar oynasi ochiladi. «Tahrirlash» tugmasini bosib miqdor, hamyon, turkum, sana yoki izohni o'zgartiring.\nHamyon qoldig'i faqat farq bo'yicha to'g'rilanadi: masalan 100 000 so'mlik xarajat 120 000 ga o'zgartirilsa, hamyondan yana 20 000 yechiladi."],
    ["Xato yozilgan amalni qanday o'chiraman?",
     "Tafsilotlar oynasida o'chirish tugmasini bosing. Amal bekor qilinadi va hamyon qoldig'i avvalgi holiga qaytadi."],
    ["Adashib o'chirib yubordim. Qaytarsa bo'ladimi?",
     "Ha. O'chirgandan keyin pastda «Qaytarish» tugmali xabar bir necha soniya turadi — uni bossangiz amal va qoldiq qayta tiklanadi.\nAgar shu orada o'sha pul boshqa joyga sarflangan bo'lsa, xarajatni qaytarib bo'lmaydi: hamyonda mablag' yetmaydi."],
    ["Nega ba'zi amallarni o'zgartirib bo'lmaydi?",
     "Agar amal o'chirilgan hamyonga tegishli bo'lsa, uni tahrirlab yoki bekor qilib bo'lmaydi — aks holda pul ko'rinmaydigan hamyonga o'tib qolardi."],
  ]},
  { id: 'recurring', icon: 'repeat', title: "Doimiy to'lovlar", items: [
    ["Doimiy to'lov nima?",
     "Ijara, kommunal, internet, obuna yoki oylik maosh kabi muntazam takrorlanadigan to'lov va tushumlar. Bir marta qo'shasiz — muddati kelganda xarajat yoki daromad o'zi yoziladi."],
    ["Qanday qo'shaman?",
     "Bosh sahifadagi «Doimiy to'lovlar» bo'limida «+ Qo'shish» tugmasini bosing. Turi, nomi, miqdor, hamyon, turkum, qanchalik tez-tez (har kuni, hafta, oy yoki yil) va birinchi to'lov sanasini tanlang."],
    ["To'lov qachon yoziladi?",
     "Muddati kelgan kuni, ilovani ochganingizda. Bir necha kun ochmagan bo'lsangiz, o'tib ketgan kunlarning hammasi yoziladi.\nBirinchi to'lov sanasi o'tmishda bo'lsa, eski sanalar orqaga qarab yozilmaydi — hisob bugundan boshlanadi."],
    ["Oyning 31-sanasidagi to'lov qisqa oylarda nima bo'ladi?",
     "O'sha oyning oxirgi kunida yoziladi (masalan 28-fevral), keyingi oyda yana 31-sanaga qaytadi."],
    ["Eslatma qanday ishlaydi?",
     "Muddatidan necha kun oldin eslatilishini o'zingiz belgilaysiz. Shu kundan boshlab navbardagi qo'ng'iroqcha belgisida xabar chiqadi."],
    ["«Avtomatik yozilmadi» degan xabar chiqdi. Nega?",
     "Odatda hamyonda pul yetmagan. To'lov keyingi safar ilovani ochganingizda yana urinib ko'riladi — hamyonni to'ldiring yoki to'lovni boshqa hamyonga o'tkazing."],
    ["Doimiy to'lovni o'chirsam nima bo'ladi?",
     "Kelgusida yozilmaydi. Avval yozilgan amallar o'chirilmaydi va qoldiq o'zgarmaydi."],
  ]},
  { id: 'goals', icon: 'target', title: 'Jamg\'arma maqsadlari', items: [
    ["Maqsad qanday ishlaydi?",
     "Yangi maqsad qo'shilganda unga alohida hamyon ochiladi — nomi maqsad nomi bilan bir xil. Yig'ilgan miqdor — shu hamyon qoldig'i. Maqsad hamyonidan xarajat qilib bo'lmaydi va maqsadni boshqa hamyonga bog'lab bo'lmaydi."],
    ["Maqsadga qanday pul qo'shaman?",
     "Maqsad kartochkasidagi «+ Pul qo'shish» tugmasini bosing — O'tkazma oynasi ochiladi, «Qaysi hamyonga» maydonida maqsad hamyoni qulflangan bo'ladi. Pul boshqa hamyondan o'tkaziladi, shuning uchun umumiy qoldiq o'zgarmaydi. Maqsad hamyoniga kirim yozib bo'lmaydi — faqat O'tkazma."],
    ["Muddat nima beradi?",
     "Maqsad kartochkasida muddatgacha necha kun qolgani ko'rinadi. Muddat ixtiyoriy."],
    ["Maqsadni o'chirsam pul yo'qoladimi?",
     "Yo'q. Maqsad hamyonida pul bo'lsa, avval u qaysi hamyonga o'tkazilishi so'raladi — pul o'sha hamyonga O'tkazma bilan o'tadi, so'ng maqsad va uning hamyoni o'chadi. Eski (oddiy hamyonga bog'langan) maqsadda faqat maqsad o'chadi, hamyon joyida qoladi."],
  ]},
  { id: 'categories', icon: 'tag', title: "Turkumlar va a'zolar", items: [
    ['Turkumlarni qayerda sozlayman?',
     "Kirim yoki Chiqim oynasidagi «Turkumlarni sozlash» tugmasini bosing. Ochilgan oynada yangi turkum qo'shish yoki keraksizini o'chirish mumkin. Kirim va xarajat turkumlari alohida."],
    ["A'zolar nima?",
     "A'zolar — siz pul sarflaydigan odamlar yoki oilalar. Ularni bosh sahifadagi «A'zolar» bo'limida qo'shasiz va xarajat yozayotganda «Kimga?» maydonida tanlaysiz. Turi «Bitta odam» yoki «Butun oila» bo'lishi mumkin."],
  ]},
  { id: 'stats', icon: 'chart', title: 'Hisobotlar', items: [
    ['Hisobotni qayerdan ko\'raman?',
     "Bosh sahifadagi hisobot kartochkasini bosing. Kunlik o'zgarish va turkumlar bo'yicha taqsimot ko'rsatiladi."],
    ['Boshqa oy yoki sana oralig\'ini tanlasa bo\'ladimi?',
     "Ha. Oyni almashtirish yoki «Dan» va «Gacha» sanalarini kiritib ixtiyoriy davrni tanlash mumkin. Davr uzunligi 1 yildan (366 kun) oshmasligi kerak."],
  ]},
  { id: 'currency', icon: 'card', title: 'Valyutalar', items: [
    ['Qaysi valyutalar bor?',
     "UZS, USD, EUR, RUB, KZT, GBP, CNY, TRY, AED, KRW, JPY va CHF. Har bir hamyon bitta valyutada yuritiladi."],
    ['Har xil valyutadagi qoldiq qanday ko\'rsatiladi?',
     "Bosh sahifada qoldiq valyutalar bo'yicha alohida chiqadi: birinchisi katta, qolganlari uning tagida. Har bir hamyon miqdori o'z valyutasida ko'rsatiladi."],
    ["Valyuta kursini qayerdan ko'raman?",
     "Navbardagi «Kurs» bo'limini bosing. Markaziy bankning bugungi kurslari ko'rsatiladi: asosiy valyutalar kartochkalarda, qolganlari «Boshqa valyutalar» ro'yxatida."],
    ["Valyuta kalkulyatori qanday ishlaydi?",
     "«Kurs» sahifasidagi «Valyuta kalkulyatori» kartasida miqdorni yozing va ikkita valyutani tanlang — natija darhol chiqadi. O'rtadagi tugma valyutalarni almashtiradi.\nHisob Markaziy bank kursi bo'yicha, bank yoki ayirboshlash shoxobchasi kursi farq qilishi mumkin."],
  ]},
  { id: 'security', icon: 'shield', title: 'Xavfsizlik va qurilmalar', items: [
    ['Parolni qanday almashtiraman?',
     "Sozlamalar → Parol bo'limida joriy parolni va yangi parolni (kamida 8 belgi) ikki marta kiriting."],
    ['Ikki bosqichli himoya nima?',
     "Yoqilgan bo'lsa, kirishda paroldan keyin elektron pochtangizga 6 xonali kod yuboriladi va u kiritilmaguncha hisob ochilmaydi. Parolingizni kimdir bilib olsa ham, elektron pochtangizga kira olmasa hisobga kira olmaydi."],
    ['Ikki bosqichli himoyani qanday yoqaman?',
     "Sozlamalar → Qurilmalar bo'limida «Ikki bosqichli himoya» yonidagi «Yoqish» tugmasini bosing, joriy parolni kiriting, so'ng elektron pochtaga kelgan kodni kiriting. Kod kelishi uchun Profil bo'limida elektron pochta kiritilgan bo'lishi kerak.\nYoqilgan paytda elektron pochtani o'chirib bo'lmaydi — aks holda kod keladigan joy qolmaydi."],
    ['Qurilmalar bo\'limi nima uchun?',
     "Bu yerda hisobingizga qaysi qurilmalardan kirilgani va kirish vaqti ko'rinadi. Notanish qurilma bo'lsa, «Boshqa qurilmalardan chiqarish» tugmasini bosing va parolni almashtiring."],
    ["Nega «Boshqa qurilmalardan chiqarish» ishlamayapti?",
     "Xavfsizlik uchun bu amalni faqat kamida 15 kun oldin kirilgan qurilmadan bajarish mumkin. Shunda parolingizni bilib olgan begona odam sizni hisobdan chiqarib yubora olmaydi."],
    ["Hisobni qanday o'chiraman?",
     "Sozlamalar → Profil bo'limida «Hisobni o'chirish» tugmasini bosing va joriy parolni kiriting. Hisob va barcha ma'lumotlaringiz (hamyonlar, kirim, chiqim, qarzlar) butunlay o'chadi — ortga qaytarib bo'lmaydi."],
    ["Hisobim o'z-o'zidan o'chib ketadimi?",
     "Ha, lekin faqat uzoq kirilmasa: 1 oy (30 kun) davomida hisobga umuman kirilmasa, hisob va barcha ma'lumotlar avtomatik o'chiriladi. Ilovani vaqti-vaqti bilan ochib turing — shunda hisob saqlanadi."],
  ]},
  { id: 'voice', icon: 'microphone', title: 'Ovozli yordamchi', items: [
    ["Ovoz bilan qanday buyruq beraman?",
     "Navbardagi mikrofon tugmasini bosing (kompyuterda Alt + M) yoki «Salom Moliya» deng — pastda dumaloq belgi chiqadi. Buyruqni oddiy gap bilan ayting: «tushlikka 45 ming sarfladim», «oylik tushdi 5 million kartaga», «kartadan naqdga 200 ming o'tkaz», «Akmalga 1 million qarz berdim».\nYordamchi savollarga ham javob beradi: «qoldig'im qancha», «bu oy ovqatga qancha ketdi», «dollar kursi qancha». «Hisobotni och», «qorong'u rejim» kabi buyruqlar ham ishlaydi."],
    ["«Salom Moliya» deb chaqirish qanday ishlaydi?",
     "U odatda yoqilgan — faqat mikrofonga bir marta ruxsat berish kerak: ilovaga kirganda pastda chiqadigan xabardagi «Ruxsat berish» tugmasini yoki navbardagi mikrofon tugmasini bosing. Shundan keyin ilova ochiq turganda «Salom Moliya» deyishingiz kifoya — dumaloq belgi ochiladi. Yordamchi faqat «Salom Moliya» deganda ochiladi — boshqa gaplarda (hatto «Moliya» so'zi aytilsa ham) yopiq turadi. O'chirish uchun Sozlamalar → Ovozli yordamchi bo'limidagi tugmani o'chiring."],
    ["Yordamchi nega javob bermasdan bajaradi?",
     "Amal bajarilganda vaqtingiz olinmasligi uchun ovozda aytilmaydi: belgi yashil bo'ladi va pastda yozilgan miqdor, turkum va hamyon bilan xabar chiqadi. Biror narsa noto'g'ri yozilgan bo'lsa, xabardagi «Bekor qilish» tugmasini bosing yoki «oxirgisini bekor qil» deng — amal o'chadi va qoldiq qaytadi."],
    ["Miqdor yoki hamyon aytilmasa nima bo'ladi?",
     "Miqdor yoki odam aytilmasa, yordamchi so'raydi: «Qancha sarfladingiz?», «Kimga qarz berdingiz?». Hamyon aytilmasa — shu yaqinda ishlatganingiz yoki odatda ishlatadiganingiz olinadi (natijada ko'rinadi); aniq bo'lmasa «Qaysi hamyondan?» deb so'raydi. Javobni ayting — masalan «50 ming», «kartadan» yoki «birinchisi». To'xtatish uchun «kerak emas» deng."],
    ["Bir gapda bir nechta amal aytsam bo'ladimi?",
     "Ha. Masalan: «tushlikka 45 ming, taksiga 20 ming sarfladim» yoki «oylik 5 million va bonus 1 million tushdi» — har biri alohida yoziladi. Hamyon bir marta aytilsa («naqddan»), hammasiga tegishli bo'ladi. Savollarni ham qo'shib so'rash mumkin: «qoldig'im va qarzlarim qancha»."],
    ["Xato yozilgan bo'lsa ovoz bilan qanday tuzataman?",
     "Amaldan keyin darhol ayting: «yo'q, 50 ming edi» — miqdor, «kartadan edi» — hamyon, «transportga o'zgartir» — turkum, «kecha edi» — sana tuzatiladi. Qoldiq ham avtomatik to'g'rilanadi.\nButunlay bekor qilish uchun «oxirgisini bekor qil» deng yoki xabardagi «Bekor qilish» tugmasini bosing."],
    ["Suhbat rejimi nima?",
     "Yordamchi javob bergandan yoki amalni bajargandan keyin yana bir necha soniya tinglaydi — keyingi buyruqni «Salom Moliya»siz aytish mumkin: «yana taksiga 20 ming». Bu paytda «bekor qil» desangiz — oxirgi amal bekor qilinadi, «rahmat» desangiz — yordamchi yopiladi. Hech narsa aytilmasa, o'zi yopiladi. Darhol yopish uchun × tugmasini, Esc ni bosing yoki ekranning boshqa istalgan joyiga teging. Yopilgan yordamchi javob bermaydi: javobi hali kelmagan buyruq bekor qilinadi. Yordamchi gapirayotganda gapirib yuborsangiz — u to'xtaydi va sizni tinglaydi.\nO'chirish: Sozlamalar → Ovozli yordamchi → «Suhbat rejimi»."],
    ["Yordamchi qanday savollarga javob beradi?",
     "Qoldiq va har bir hamyon («qoldig'im qancha»), sarf va kirim («bu oy qancha sarfladim»), eng ko'p xarajat turkumlari («eng ko'p nimaga sarfladim»), kun xulosasi («bugungi xulosa»), o'tgan oy bilan taqqoslash («o'tgan oyga nisbatan qanday»), qarzlar, jamg'arma maqsadlari («maqsadimga qancha qoldi»), yaqin doimiy to'lovlar («keyingi to'lovlar qachon») va valyuta kursi. Ro'yxatlar dumaloq belgi ustidagi kartada ko'rinadi."],
    ["Ruscha gapirsam tushunadimi?",
     "Ha, asosiy buyruqlarni tushunadi: «потратил на обед 45 тысяч», «получил зарплату 5 миллионов», «перевёл с карты на наличные 200 тысяч», «сколько я потратил». Javoblar o'zbekcha bo'ladi."],
    ["Ovozim yoziladimi yoki saqlanadimi?",
     "Ilova ovozni saqlamaydi. Odatda ovozni brauzerning o'zi matnga aylantiradi (Chrome va Edge'da — Google, Safari'da — Apple xizmati orqali) va serverga faqat tanilgan matn yuboriladi. Brauzer gapni tanimasa yoki noto'g'ri tanisa, aniqroq tanish uchun shu gapning ovoz yozuvi server orqali OpenAI xizmatiga yuboriladi va javobdan keyin o'chiriladi. «Salom Moliya» yoqilgan bo'lsa, ilova ochiq turgan paytda mikrofon chaqiruv so'zini kutadi — brauzer buni manzil satridagi belgi bilan ko'rsatadi."],
    ["Yordamchining ovozini o'zgartirsa bo'ladimi?",
     "Ha. Sozlamalar → Ovozli yordamchi bo'limidagi «Yordamchi ovozi» dan Madina (ayol) yoki Sardor (erkak) ni tanlang — namunaviy gap shu ovozda o'qiladi. Tanlov shu brauzerda saqlanadi.\nJavoblar ravon o'zbekcha ovozda o'qilishi uchun server ovozi yoqilgan bo'lishi kerak. U bo'lmasa brauzerning o'z ovozi ishlatiladi: o'zbekcha ovoz faqat Edge brauzerida bor, boshqalarida javob g'alati eshitilishi mumkin."],
    ["Qaysi brauzerda ishlaydi?",
     "Chrome, Edge va Safari'da (telefon va kompyuterda) brauzerning o'zi taniydi. Firefox'da yoki brauzer tanimay qolsa, ovoz server orqali taniladi (agar administrator buni yoqqan bo'lsa); aks holda dumaloq belgi ochilganda buyruqni yozib yuborishingiz mumkin. «Salom Moliya» deb chaqirish faqat brauzer o'zi taniydigan joyda ishlaydi. Mikrofon faqat xavfsiz (https://) manzilda ishlaydi. Shovqinli joyda yoki ovoz tanilmasa, belgi yonidagi yozish tugmasidan foydalaning."],
  ]},
  { id: 'look', icon: 'note', title: "Ko'rinish va til", items: [
    ["Yorug' yoki qorong'u rejimni qanday almashtiraman?",
     "Navbardagi quyosh/oy tugmasini bosing. Tanlov shu brauzerda saqlanadi."],
    ['Ranglarni qanday o\'zgartiraman?',
     "Sozlamalar → Ranglar bo'limida mavzuni tanlang — u darhol qo'llanadi. Har bir mavzu yorug' va qorong'u rejimda ishlaydi."],
    ['Ilova tilini qanday almashtiraman?',
     "Sozlamalar → Til bo'limida tilni tanlang. O'zbek, tojik, qozoq, qirg'iz, rus, ingliz va turk tillari bor. Tanlangan til shu brauzerda saqlanadi."],
  ]},
];

function showHelpTopics() {
  delete document.getElementById('settingsHelp').dataset.topic;
  document.getElementById('settingsSubTitle').textContent = settingsMenuLabel('help');
  const body = document.getElementById('helpBody');
  body.innerHTML = `<div class="help-list">${HELP_TOPICS.map(t => `
    <button type="button" class="help-row" data-help-topic="${t.id}">
      <span class="help-row-icon">${icon(t.icon)}</span>
      <span class="help-row-text">${escapeHtml(t.title)}</span>
      ${icon('chevronRight')}
    </button>`).join('')}</div>`;
  body.scrollTop = 0;
}

function showHelpTopic(id) {
  const topic = HELP_TOPICS.find(t => t.id === id);
  if (!topic) return;
  document.getElementById('settingsHelp').dataset.topic = id;
  document.getElementById('settingsSubTitle').textContent = topic.title;
  const body = document.getElementById('helpBody');
  // <details> — klaviatura va ekran o'quvchilar uchun tayyor ochiladigan blok, JS kerak emas
  body.innerHTML = `<div class="help-list">${topic.items.map(([q, a]) => `
    <details class="help-item">
      <summary>${escapeHtml(q)}${icon('chevronDown')}</summary>
      <div class="help-answer">${a.split('\n').map(p => `<p>${escapeHtml(p)}</p>`).join('')}</div>
    </details>`).join('')}</div>`;
  body.scrollTop = 0;
}

document.getElementById('helpBody')?.addEventListener('click', e => {
  const row = e.target.closest('[data-help-topic]');
  if (row) showHelpTopic(row.dataset.helpTopic);
});
// Ma'lumotnomada mavzu ochiq bo'lsa avval mavzular ro'yxatiga, aks holda bo'limlar ro'yxatiga qaytadi
document.getElementById('btnSettingsBack')?.addEventListener('click', () => {
  const help = document.getElementById('settingsHelp');
  if (!help.hidden && help.dataset.topic) showHelpTopics();
  else switchSettingsTab(null);
});

// ==========================================
// CHAT YORDAMCHILARI (Moliya yordamchisi va Yordam uchun umumiy)
// ==========================================
// Matn har doim textContent bilan qo'yiladi — foydalanuvchi yoki yordamchi yozgan HTML ishlamaydi
function chatMessageEl({ text, mine, time, error }) {
  const row = document.createElement('div');
  row.className = `chat-msg ${mine ? 'is-mine' : 'is-theirs'}${error ? ' is-error' : ''}`;
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.textContent = text;
  row.appendChild(bubble);
  if (time) {
    const t = document.createElement('div');
    t.className = 'chat-time';
    t.textContent = time;
    row.appendChild(t);
  }
  return row;
}

function chatTypingEl() {
  const row = document.createElement('div');
  row.className = 'chat-msg is-theirs';
  row.innerHTML = '<div class="chat-bubble"><span class="chat-typing" aria-label="Yozmoqda"><i></i><i></i><i></i></span></div>';
  return row;
}

function chatScrollToEnd(log) {
  log.scrollTop = log.scrollHeight;
}

// Yozish maydoni matnga qarab 1–5 qatorgacha o'sadi; Enter — yuborish, Shift+Enter — yangi qator
function setupChatInput(textarea, form) {
  if (!textarea || !form) return;
  const grow = () => {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    textarea.style.overflowY = textarea.scrollHeight > 120 ? 'auto' : 'hidden';
  };
  textarea.addEventListener('input', grow);
  textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
  textarea._grow = grow;
}

// ==========================================
// MOLIYA YORDAMCHISI (Sozlamalar → Moliya yordamchisi)
// ==========================================
// Suhbat faqat xotirada (sahifa yangilanguncha) — serverda saqlanmaydi. Javob ma'lumotnomadan qidiriladi (mainapp/faq.py)
const assistantState = { messages: [] };

function renderAssistant() {
  const log = document.getElementById('assistantLog');
  log.innerHTML = '';
  if (!assistantState.messages.length) {
    log.innerHTML = `<div class="chat-empty">${icon('sparkle')}
      <p class="chat-empty-title">Moliya yordamchisi</p>
      <p>Hamyonlar, kirim va chiqim, qarzlar, valyutalar va sozlamalar bo'yicha savolingizni yozing — ilovadan qanday foydalanishni tushuntirib beraman.</p>
    </div>`;
    return;
  }
  assistantState.messages.forEach(m => log.appendChild(chatMessageEl({ text: m.content, mine: m.role === 'user', error: m.error })));
  chatScrollToEnd(log);
}

function openAssistant() {
  renderAssistant();
  const input = document.getElementById('assistantInput');
  input._grow?.();  // yashirin turganda hisoblangan balandlik noto'g'ri bo'ladi — ko'ringach qayta o'lchanadi
  input.focus();
}

// Pastki o'ngdagi dumaloq tugma: Moliya yordamchisi har sahifada. Chat elementlari (suhbat, forma) bitta — Sozlamalar
// bo'limi bilan oyna orasida ko'chiriladi: suhbat ham, forma tinglovchilari ham ikkala joyda umumiy
function setAssistantDock(open) {
  const dock = document.getElementById('assistantDock');
  const fab = document.getElementById('assistantFab');
  if (!dock || open === !dock.hidden) return;
  const settingsPanel = document.getElementById('settingsAssistant');
  const dockBody = document.getElementById('assistantDockBody');
  const [from, to] = open ? [settingsPanel, dockBody] : [dockBody, settingsPanel];
  while (from.firstChild) to.appendChild(from.firstChild);
  dock.hidden = !open;
  fab.setAttribute('aria-expanded', String(open));
  if (open) openAssistant();
}

// Kirgan foydalanuvchiga ko'rinadi (checkAuth)
function setAssistantFab(visible) {
  const fab = document.getElementById('assistantFab');
  if (!fab) return;
  if (!visible) setAssistantDock(false);
  fab.hidden = !visible;
  document.body.classList.toggle('has-assistant-fab', visible);
}

document.getElementById('assistantFab')?.addEventListener('click', () => {
  setAssistantDock(document.getElementById('assistantDock').hidden);
});
document.getElementById('assistantDockClose')?.addEventListener('click', () => {
  setAssistantDock(false);
  document.getElementById('assistantFab').focus();
});
// Sahifaning boshqa joyiga bosish oynani yopmaydi: yordamchi bilan gaplashib turib ilovadan foydalanish mumkin.
// Yopish — faqat × yoki dumaloq tugma (va klaviaturada Esc)
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || document.getElementById('assistantDock')?.hidden !== false) return;
  e.preventDefault(); // Esc faqat yordamchi oynasini yopadi
  setAssistantDock(false);
  document.getElementById('assistantFab').focus();
});

async function askAssistant(question) {
  const log = document.getElementById('assistantLog');
  assistantState.messages.push({ role: 'user', content: question });
  renderAssistant();
  log.appendChild(chatTypingEl());
  chatScrollToEnd(log);
  // Xato javoblar tarixga kirmaydi — keyingi so'rovda modelga yuborilmaydi
  const history = assistantState.messages.filter(m => !m.error).map(({ role, content }) => ({ role, content }));
  let reply;
  try {
    const res = await fetch(`${API_BASE}/assistant/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) reply = { role: 'assistant', content: data.answer };
    else if (res.status === 429) reply = { role: 'assistant', content: "Juda ko'p savol berildi. Birozdan keyin qayta urinib ko'ring.", error: true };
    else reply = { role: 'assistant', content: data.error || "Javob olinmadi. Qayta urinib ko'ring.", error: true };
  } catch (e) {
    reply = { role: 'assistant', content: NETWORK_ERROR_MESSAGE, error: true };
  }
  assistantState.messages.push(reply);
  renderAssistant();
}

onSubmitOnce('formAssistant', async () => {
  const input = document.getElementById('assistantInput');
  const question = input.value.trim();
  if (!question) return;
  input.value = '';
  input._grow?.();
  await askAssistant(question);
  input.focus();
});
setupChatInput(document.getElementById('assistantInput'), document.getElementById('formAssistant'));

// ==========================================
// YORDAM — admin bilan chat (Sozlamalar → Yordam)
// ==========================================
// Admin javobni admin panelidan yozadi. Bo'lim ochiq turganda yangi xabarlar har SUPPORT_POLL_MS da so'raladi;
// o'qilmagan javoblar soni navbar qo'ng'irog'ida ko'rinadi (SUPPORT_UNREAD_POLL_MS da yangilanadi)
const SUPPORT_POLL_MS = 5000;
const SUPPORT_UNREAD_POLL_MS = 60000;
const supportState = { lastId: 0, loaded: false, timer: null, unreadTimer: null };

function supportPanelOpen() {
  return document.getElementById('modalSettings').classList.contains('active')
    && !document.getElementById('settingsSupport').hidden;
}

function renderSupportEmpty() {
  document.getElementById('supportLog').innerHTML = `<div class="chat-empty">${icon('chat')}
    <p>Savol, muammo yoki taklifingizni yozing — admin shu yerda javob beradi.</p></div>`;
}

function appendSupportMessages(messages) {
  const log = document.getElementById('supportLog');
  const fresh = messages.filter(m => m.id > supportState.lastId);
  if (!fresh.length) return;
  log.querySelector('.chat-empty')?.remove();
  const atEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 60;
  fresh.forEach(m => {
    log.appendChild(chatMessageEl({
      text: m.text, mine: !m.from_admin,
      time: `${m.from_admin ? 'Admin · ' : ''}${formatUzDate(m.created_at, { year: true, time: true })}`,
    }));
    supportState.lastId = m.id;
  });
  if (atEnd) chatScrollToEnd(log);
}

function stopSupportPolling() {
  clearInterval(supportState.timer);
  supportState.timer = null;
}

async function pollSupport() {
  if (!supportPanelOpen()) return stopSupportPolling();
  if (document.hidden) return;
  try {
    const res = await fetch(`${API_BASE}/support/messages/?after=${supportState.lastId}`);
    if (!res.ok) return;
    const data = await res.json();
    appendSupportMessages(data.messages);
    // Ochiq suhbatdagi admin javoblari server tomonida o'qilgan deb belgilandi
    if (data.messages.some(m => m.from_admin)) setSupportUnread(0);
  } catch (e) { /* tarmoq uzilgan — keyingi urinishda */ }
}

async function openSupport() {
  const log = document.getElementById('supportLog');
  if (!supportState.loaded) {
    log.innerHTML = '';
    log.appendChild(chatTypingEl());
    try {
      const res = await fetch(`${API_BASE}/support/messages/`);
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      log.innerHTML = '';
      supportState.loaded = true;
      if (data.messages.length) appendSupportMessages(data.messages);
      else renderSupportEmpty();
    } catch (e) {
      log.innerHTML = '';
      log.appendChild(chatMessageEl({ text: NETWORK_ERROR_MESSAGE, error: true }));
      return;
    }
  } else {
    await pollSupport();
  }
  setSupportUnread(0);
  chatScrollToEnd(log);
  document.getElementById('supportInput').focus();
  stopSupportPolling();
  supportState.timer = setInterval(pollSupport, SUPPORT_POLL_MS);
}

onSubmitOnce('formSupport', async () => {
  const input = document.getElementById('supportInput');
  const text = input.value.trim();
  if (!text) return;
  try {
    const res = await fetch(`${API_BASE}/support/messages/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showToast(res.status === 429 ? "Juda ko'p xabar yuborildi. Birozdan keyin qayta urinib ko'ring." : (data.error || 'Xabar yuborilmadi'), 'error');
      return;
    }
    input.value = '';
    input._grow?.();
    // Yuborilgan xabardan oldin kelgan javoblar ham tartib bilan chiqsin
    await pollSupport();
    appendSupportMessages([data]);
    chatScrollToEnd(document.getElementById('supportLog'));
  } catch (e) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
  input.focus();
});
setupChatInput(document.getElementById('supportInput'), document.getElementById('formSupport'));

// O'qilmagan admin javoblari: navbar qo'ng'irog'i va Sozlamalardagi "Yordam" qatori
function setSupportUnread(count) {
  state.supportUnread = count;
  const badge = document.getElementById('supportMenuBadge');
  if (badge) {
    badge.hidden = !count;
    badge.textContent = count > 99 ? '99+' : count;
  }
  renderNotifications();
}

async function refreshSupportUnread() {
  if (!state.currentUser || document.hidden || supportPanelOpen()) return;
  try {
    const res = await fetch(`${API_BASE}/support/unread/`);
    if (!res.ok) return;
    const { unread, notices_unread: noticesUnread } = await res.json();
    if (unread !== state.supportUnread) setSupportUnread(unread);
    if (noticesUnread !== state.noticesUnread) fetchNotices();
  } catch (e) { /* tarmoq uzilgan */ }
}

// Kirishda (checkAuth) boshlanadi, chiqishda to'xtaydi; suhbatlar xotirasi ham tozalanadi
function startSupportUnreadPolling(initial) {
  setSupportUnread(initial || 0);
  clearInterval(supportState.unreadTimer);
  supportState.unreadTimer = setInterval(refreshSupportUnread, SUPPORT_UNREAD_POLL_MS);
}

function stopSupportUnreadPolling() {
  clearInterval(supportState.unreadTimer);
  stopSupportPolling();
  Object.assign(supportState, { unreadTimer: null, loaded: false, lastId: 0 });
  assistantState.messages = [];
  state.supportUnread = 0;
  state.notices = [];
  state.noticesUnread = 0;
}

// ==========================================
// QURILMALAR (Sozlamalar → Qurilmalar)
// ==========================================
function deviceName(d) {
  return [d.browser, d.os].filter(Boolean).join(' · ') || "Noma'lum qurilma";
}

function renderDevices(data) {
  const list = document.getElementById('deviceList');
  const others = data.devices.filter(d => !d.current).length;
  list.innerHTML = data.devices.map(d => `
    <div class="device-item${d.current ? ' is-current' : ''}">
      <span class="device-icon">${icon(d.kind)}</span>
      <div class="device-info">
        <div class="device-name"><span>${escapeHtml(deviceName(d))}</span>${d.current ? '<span class="device-badge">Bu qurilma</span>' : ''}</div>
        <div class="device-meta">Kirgan: ${escapeHtml(formatUzDate(d.created_at, { year: true, time: true }))}</div>
        <div class="device-meta"><span>${d.current
          ? 'Hozir faol'
          : `Oxirgi faollik: ${escapeHtml(formatUzDate(d.last_seen, { year: true, time: true }))}`}</span>${d.ip ? `<span> · IP: ${escapeHtml(d.ip)}</span>` : ''}</div>
      </div>
      ${d.current ? '' : `<button type="button" class="btn btn-subtle btn-xs device-end" data-device-end="${d.id}"${data.can_terminate ? '' : ' disabled'}>Chiqarish</button>`}
    </div>`).join('');

  const hint = document.getElementById('deviceLockHint');
  // Chiqarish taqiqlangan bo'lsa sababi va qachon ruxsat berilishi ko'rsatiladi
  hint.hidden = data.can_terminate || !others;
  if (!hint.hidden) {
    hint.textContent = `Boshqa qurilmalardan chiqarish uchun bu qurilmada kamida ${data.min_days} kun oldin kirilgan bo'lishi kerak. `
      + `Ruxsat: ${formatUzDate(data.terminate_allowed_at, { year: true, time: true })}`;
  }
  const btnOthers = document.getElementById('btnTerminateOthers');
  btnOthers.hidden = !others;
  btnOthers.disabled = !data.can_terminate;
}

async function loadDevices() {
  const list = document.getElementById('deviceList');
  list.innerHTML = '<div class="device-empty">Yuklanmoqda...</div>';
  try {
    const res = await fetch(`${API_BASE}/auth/devices/`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    renderDevices(await res.json());
  } catch (err) {
    list.innerHTML = `<div class="device-empty">Qurilmalarni yuklab bo'lmadi.
      <button type="button" class="btn btn-subtle btn-xs" id="btnDevicesRetry">Qayta urinish</button></div>`;
    document.getElementById('btnDevicesRetry')?.addEventListener('click', loadDevices);
  }
}

async function terminateDevices(url, confirmMessage, okMessage) {
  const sure = await showConfirm({ title: 'Qurilmani chiqarish', message: confirmMessage, confirmText: 'Ha, chiqarish', cancelText: "Yo'q" });
  if (!sure) return;
  try {
    const res = await fetch(url, { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    if (res.ok) showToast(okMessage);
    else showToast(extractErrorMessage(data, 'Qurilmani chiqarishda xatolik'), 'error');
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
  loadDevices();
}

document.getElementById('deviceList')?.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-device-end]');
  if (!btn || btn.disabled) return;
  terminateDevices(`${API_BASE}/auth/devices/${Number(btn.dataset.deviceEnd)}/terminate/`,
    'Bu qurilma hisobdan chiqariladi. Unda qayta kirish uchun parol kerak bo\'ladi.', 'Qurilma chiqarildi');
});

document.getElementById('btnTerminateOthers')?.addEventListener('click', () => {
  terminateDevices(`${API_BASE}/auth/devices/terminate-others/`,
    'Bu qurilmadan boshqa barcha qurilmalar hisobdan chiqariladi.', 'Boshqa barcha qurilmalar chiqarildi');
});

const PROFILE_FIELD_IDS = ['settingsFirstName', 'settingsLastName', 'settingsUsername', 'settingsEmail', 'settingsPhone'];

// Profil maydonlari saqlangan ma'lumot bilan to'ldiriladi (ochilganda va "Bekor qilish" bosilganda)
function fillProfileForm(user) {
  document.getElementById('settingsFirstName').value = user.first_name || '';
  document.getElementById('settingsLastName').value = user.last_name || '';
  document.getElementById('settingsUsername').value = user.username || '';
  document.getElementById('settingsEmail').value = user.email || '';
  document.getElementById('settingsPhone').value = user.phone || '';
  document.getElementById('settingsEmailPassword').value = '';
  setEmailConfirm(null);
  updateEmailPasswordField();
}

// Ko'rish rejimida maydonlar faqat o'qiladi; bo'sh maydonda namuna ("+998 90...") qiymatdek ko'rinmasligi uchun
// "Kiritilmagan" yoziladi. Tahrirlashda asl namunalar qaytadi
function setProfileMode(mode) {
  const editing = mode === 'edit';
  document.getElementById('formSettingsProfile').dataset.mode = editing ? 'edit' : 'view';
  PROFILE_FIELD_IDS.forEach(id => {
    const input = document.getElementById(id);
    input.dataset.editPlaceholder ??= input.placeholder;
    input.readOnly = !editing;
    input.placeholder = editing ? input.dataset.editPlaceholder : 'Kiritilmagan';
  });
}

function openSettings() {
  const user = state.currentUser;
  if (!user) return;
  switchSettingsTab(null);
  openModal('modalSettings');
}

document.getElementById('btnProfileEdit')?.addEventListener('click', () => {
  setProfileMode('edit');
  document.getElementById('settingsFirstName').focus();
});

// O'zgarishlar bekor qilinadi, oyna yopilmaydi — ko'rish rejimiga qaytadi
document.getElementById('btnProfileCancel')?.addEventListener('click', () => {
  if (state.currentUser) fillProfileForm(state.currentUser);
  setProfileMode('view');
  document.getElementById('btnProfileEdit').focus();
});

// Email o'zgartirilsa joriy parol so'raladi (server ham shuni talab qiladi — email parolni tiklash kanali)
function settingsEmailChanged() {
  const typed = document.getElementById('settingsEmail').value.trim().toLowerCase();
  return typed !== (state.currentUser?.email || '').toLowerCase();
}

function updateEmailPasswordField() {
  const changed = settingsEmailChanged() && !_emailConfirm.token;
  document.getElementById('settingsEmailPasswordGroup').hidden = !changed;
  document.getElementById('settingsEmailPassword').required = changed;
}

// Ikki bosqichli kirish yoqilgan bo'lsa server yangi emailni darhol saqlamaydi: unga kod yuboradi (email_pending).
// Shu holatda "Saqlash" kodni tasdiqlaydi (/auth/profile/confirm-email/)
let _emailConfirm = { token: null };

function setEmailConfirm(pending) {
  _emailConfirm.token = pending?.token || null;
  const group = document.getElementById('settingsEmailCodeGroup');
  const input = document.getElementById('settingsEmailCode');
  group.hidden = !_emailConfirm.token;
  input.required = !!_emailConfirm.token;
  input.value = '';
  if (pending) document.getElementById('settingsEmailCodeLabel').textContent = `${pending.email} ga kelgan kod *`;
}

document.getElementById('settingsEmail')?.addEventListener('input', () => {
  // Email yana o'zgartirilsa eski kod endi bu manzilga tegishli emas — qaytadan parol bilan saqlanadi
  if (_emailConfirm.token) setEmailConfirm(null);
  updateEmailPasswordField();
});

document.getElementById('btnOpenSettings')?.addEventListener('click', openSettings);

document.querySelectorAll('#settingsMenu [data-settings-tab]').forEach(btn => {
  btn.addEventListener('click', () => switchSettingsTab(btn.dataset.settingsTab));
});

onSubmitOnce('formSettingsProfile', async (e) => {
  e.preventDefault();
  // Ko'rish rejimida maydonda Enter bosilsa ham forma yuboriladi — bu holatda hech narsa saqlanmaydi
  if (e.target.dataset.mode !== 'edit') return;
  if (_emailConfirm.token) {
    await confirmProfileEmail();
    return;
  }
  const payload = {
    first_name: document.getElementById('settingsFirstName').value.trim(),
    last_name: document.getElementById('settingsLastName').value.trim(),
    username: document.getElementById('settingsUsername').value.trim(),
    email: document.getElementById('settingsEmail').value.trim(),
    phone: document.getElementById('settingsPhone').value.trim(),
  };
  if (settingsEmailChanged()) {
    payload.password = document.getElementById('settingsEmailPassword').value.trim();
  }

  try {
    const res = await fetch(`${API_BASE}/auth/profile/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.email_pending) {
      // Boshqa maydonlar saqlandi, email esa kod tasdiqlangach yoziladi: forma tahrir rejimida qoladi
      state.currentUser = data.user;
      renderUserNav();
      document.getElementById('settingsEmailPassword').value = '';
      setEmailConfirm(data.email_pending);
      updateEmailPasswordField();
      showToast(data.message);
      document.getElementById('settingsEmailCode').focus();
    } else if (res.ok) {
      state.currentUser = data.user;
      renderUserNav();
      showToast("Profil ma'lumotlari saqlandi");
      // Oyna ochiq qoladi: saqlangan qiymatlar ko'rish rejimida ko'rinadi
      fillProfileForm(data.user);
      setProfileMode('view');
      document.getElementById('btnProfileEdit').focus();
    } else {
      showToast(extractErrorMessage(data, 'Profilni saqlashda xatolik'), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

async function confirmProfileEmail() {
  try {
    const res = await fetch(`${API_BASE}/auth/profile/confirm-email/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: _emailConfirm.token,
        code: document.getElementById('settingsEmailCode').value.replace(/\D/g, ''),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      state.currentUser = data.user;
      renderUserNav();
      showToast(data.message || 'Elektron pochta yangilandi');
      fillProfileForm(data.user);
      setProfileMode('view');
      document.getElementById('btnProfileEdit').focus();
    } else {
      showToast(extractErrorMessage(data, 'Kodni tasdiqlashda xatolik'), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
}

onSubmitOnce('formSettingsPassword', async (e) => {
  e.preventDefault();
  const oldPassword = document.getElementById('settingsOldPassword').value.trim();
  const newPassword = document.getElementById('settingsNewPassword').value.trim();
  const newPassword2 = document.getElementById('settingsNewPassword2').value.trim();

  if (newPassword !== newPassword2) {
    showToast('Yangi parollar bir-biriga mos kelmadi', 'error');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/change-password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast("Parol o'zgartirildi");
      e.target.reset();
      closeModal('modalSettings');
    } else {
      showToast(extractErrorMessage(data, "Parolni o'zgartirishda xatolik"), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// Logout Button
document.getElementById('btnLogout')?.addEventListener('click', async () => {
  const sure = await showConfirm({
    title: 'Tizimdan chiqish',
    message: 'Tizimdan chiqishni xohlaysizmi?',
    confirmText: 'Ha, chiqish',
    cancelText: "Yo'q",
    danger: false,
  });
  if (!sure) return;
  try {
    const res = await fetch(`${API_BASE}/auth/logout/`, {
      method: 'POST'
    });
    // 401 — sessiya allaqachon tugagan: foydalanuvchi baribir chiqqan, kirish oynasiga qaytariladi
    if (res.ok || res.status === 401) reloadSignedOut('Tizimdan muvaffaqiyatli chiqildi');
    else showToast(extractErrorMessage(await res.json().catch(() => ({})), 'Tizimdan chiqishda xatolik'), 'error');
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// Akkauntni o'chirish: tugma alohida tasdiqlash oynasini ochadi (parol so'raydi)
document.getElementById('btnDeleteAccount')?.addEventListener('click', () => {
  document.getElementById('formDeleteAccount').reset();
  openModal('modalDeleteAccount');
  document.getElementById('deleteAccountPassword').focus();
});

onSubmitOnce('formDeleteAccount', async (e) => {
  e.preventDefault();
  const password = document.getElementById('deleteAccountPassword').value.trim();

  try {
    const res = await fetch(`${API_BASE}/auth/delete-account/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      reloadSignedOut("Hisob o'chirildi");
    } else {
      showToast(extractErrorMessage(data, "Hisobni o'chirishda xatolik"), 'error');
    }
  } catch (err) {
    showToast(NETWORK_ERROR_MESSAGE, 'error');
  }
});

// Password Visibility Toggle (Show / Hide)
document.querySelectorAll('.toggle-password-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const targetId = btn.getAttribute('data-target');
    const input = document.getElementById(targetId);
    if (!input) return;

    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';

    const eyeShow = btn.querySelector('.eye-show');
    const eyeHide = btn.querySelector('.eye-hide');
    if (eyeShow && eyeHide) {
      eyeShow.style.display = isPassword ? 'none' : 'block';
      eyeHide.style.display = isPassword ? 'block' : 'none';
    }
    btn.title = isPassword ? "Parolni yashirish" : "Parolni ko'rsatish";
  });
});

// Initial boot
document.addEventListener('DOMContentLoaded', () => {
  showFlashMessage();
  fetchCategories();
  checkAuth();
});




// Sahifa eng tepasida navbar soyasiz, aylantirilganda soya oladi (style.css: .navbar.at-top)
const _navbarEl = document.querySelector('.navbar');
function syncNavbarAtTop() {
  _navbarEl?.classList.toggle('at-top', window.scrollY <= 4);
}
window.addEventListener('scroll', syncNavbarAtTop, { passive: true });
syncNavbarAtTop();

// Navbar doim ko'rinib turadi: ro'yxat sahifalari (overlay) kontenti uning ostidan boshlanishi uchun balandligini kuzatib boramiz.
// Navbar balandligi kirgandan keyin (bo'limlar kapsulasi chiqadi), shrift yuklanganda va ekran eni o'zgarganda o'zgaradi.
// Faqat ResizeObserver'ga ishonilmaydi: u ba'zan (fon varaqda) kechikadi va eski qiymat qolib, sahifa navbar ostida qolardi —
// shuning uchun sahifa ochilganda ham qayta o'lchanadi
const _navEl = document.querySelector('.navbar');
let _navbarObserver = null;  // havola saqlanadi — kuzatuvchi yig'ishtirib yuborilmasin
function syncNavbarHeight() {
  if (_navEl) document.documentElement.style.setProperty('--navbar-h', _navEl.getBoundingClientRect().height + 'px');
}
syncNavbarHeight();
if (_navEl && 'ResizeObserver' in window) {
  _navbarObserver = new ResizeObserver(syncNavbarHeight);
  _navbarObserver.observe(_navEl, { box: 'border-box' });
}
window.addEventListener('resize', syncNavbarHeight);
window.addEventListener('load', syncNavbarHeight);
document.fonts?.ready.then(syncNavbarHeight);
// Sahifa (overlay) ochilishi bilan — bitta joyda, har bir open* funksiyasiga yozmasdan
const _txOverlayEl = document.getElementById('txPageOverlay');
if (_txOverlayEl) {
  new MutationObserver(() => { if (_txOverlayEl.classList.contains('open')) syncNavbarHeight(); })
    .observe(_txOverlayEl, { attributes: true, attributeFilter: ['class'] });
}

// "Shisha" tugmacha (style.css: .glass-thumb) — segmentli guruhlar (.segmented) va navbar bo'limlari (.nav-sections).
// Tugmachaning o'rni va eni faol tugmadan o'lchanadi (--thumb-x / --thumb-w), chunki filtrlardagi tugmalar har xil enda.
// .active / .is-active ni qaysi handler almashtirsa ham kuzatiladi: bosilganda tugmacha linzaga aylanib yangi bo'limga
// suzib o'tadi, bo'lim ochilganda yoki eni o'zgarganda esa animatsiyasiz joyida turadi.
// Barmoq yoki sichqoncha bilan surilsa linza unga ergashadi; qo'yib yuborilgan joydagi tugma bosiladi (.click())
const GLASS_LIFT_MS = 420;
// Suzish davomiyligi (style.css: .glass-thumb transition 0.5s) — shu vaqt ichida o'lcham o'zgarsa ham silliq davom etadi
const GLASS_SLIDE_MS = 550;
const GLASS_DRAG_PX = 6;
const _reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)');

function glassActive(track) {
  return track.querySelector(':scope > .active, :scope > .is-active');
}

function glassButtons(track) {
  return [...track.querySelectorAll(':scope > button')].filter(b => !b.disabled);
}

function setThumb(track, x, w) {
  track.style.setProperty('--thumb-x', x + 'px');
  track.style.setProperty('--thumb-w', w + 'px');
}

function dropGlassLater(g) {
  clearTimeout(g.dropTimer);
  g.dropTimer = setTimeout(() => { if (!g.drag) g.thumb.classList.remove('is-lifted'); }, GLASS_LIFT_MS);
}

function placeGlassThumb(track, animate) {
  const g = track._glass;
  const active = glassActive(track);
  const changed = active !== g.active;
  g.active = active;
  track.classList.toggle('has-active', !!active);
  track.classList.toggle('is-scrollable', track.scrollWidth > track.clientWidth + 1);
  if (!active) {
    g.shown = false;
    return;
  }
  // Avval hech biri tanlanmagan bo'lsa (navbar boshqa sahifada) tugmacha chetdan suzib kelmasin — joyida paydo bo'ladi
  const instant = !animate || !g.shown || _reducedMotion?.matches;
  if (instant) g.thumb.classList.add('no-anim');
  setThumb(track, active.offsetLeft, active.offsetWidth);
  if (instant) {
    void g.thumb.offsetWidth;  // yangi o'rin animatsiyasiz qo'llansin
    g.thumb.classList.remove('no-anim');
  }
  g.shown = true;
  if (animate && changed && !instant) {
    g.thumb.classList.add('is-lifted');
    dropGlassLater(g);
    g.slideUntil = performance.now() + GLASS_SLIDE_MS;
  }
}

// O'lcham o'zgardi (ekran eni, ochilgan oyna). Tab almashganda ro'yxat ham yangilanadi va aylantirish chizig'i
// paydo bo'lib/yo'qolib eni bir necha pikselga o'zgaradi: suzayotgan tugmacha shunda sakrab qolmasin — yangi
// o'lchamga silliq suzishda davom etadi. Boshqa paytda (oyna ochildi, ekran burildi) joyiga darhol qo'yiladi
function onGlassResize(track) {
  const g = track._glass;
  if (g.drag) return;
  placeGlassThumb(track, performance.now() < (g.slideUntil || 0));
}

// Linza markaziga eng yaqin tugma
function glassButtonAt(track, clientX) {
  let best = null;
  let bestDist = Infinity;
  for (const btn of glassButtons(track)) {
    const r = btn.getBoundingClientRect();
    const dist = Math.abs(clientX - (r.left + r.width / 2));
    if (dist < bestDist) { best = btn; bestDist = dist; }
  }
  return best;
}

function moveGlassLens(track, clientX) {
  const g = track._glass;
  const btn = glassButtonAt(track, clientX);
  if (!btn) return;
  const buttons = glassButtons(track);
  const first = buttons[0];
  const last = buttons[buttons.length - 1];
  const w = btn.offsetWidth;
  const x = clientX - track.getBoundingClientRect().left - track.clientLeft + track.scrollLeft - w / 2;
  setThumb(track, Math.min(Math.max(x, first.offsetLeft), last.offsetLeft + last.offsetWidth - w), w);
  if (btn !== g.drag.over) {
    g.drag.over?.classList.remove('is-under-lens');
    btn.classList.add('is-under-lens');
    g.drag.over = btn;
  }
}

function endGlassDrag(track, cancelled) {
  const g = track._glass;
  const drag = g.drag;
  if (!drag) return;
  g.drag = null;
  drag.over?.classList.remove('is-under-lens');
  g.thumb.classList.remove('is-dragging');
  if (drag.moved && !cancelled && drag.over && drag.over !== glassActive(track)) {
    // Surish oxiridagi brauzer "click"i (boshlangan tugmaga) ikkinchi marta bosilmasin
    g.suppressClick = true;
    setTimeout(() => { g.suppressClick = false; }, 0);
    drag.over.click();
  }
  placeGlassThumb(track, true);
  dropGlassLater(g);
}

function initGlassTrack(track) {
  if (track._glass) return;
  const thumb = document.createElement('span');
  thumb.className = 'glass-thumb';
  thumb.setAttribute('aria-hidden', 'true');
  track.append(thumb);
  const g = track._glass = { thumb, active: undefined, shown: false, drag: null, dropTimer: 0, suppressClick: false };
  track.classList.add('has-glass');
  placeGlassThumb(track, false);

  // Faqat faol bo'lim almashganda (linza ostidagi .is-under-lens ham klass, lekin u tugmachani siljitmasligi kerak)
  new MutationObserver(() => {
    if (!g.drag && glassActive(track) !== g.active) placeGlassThumb(track, true);
  }).observe(track, { subtree: true, attributes: true, attributeFilter: ['class'] });
  if ('ResizeObserver' in window) {
    const ro = new ResizeObserver(() => onGlassResize(track));
    ro.observe(track);
    glassButtons(track).forEach(btn => ro.observe(btn));
  }

  track.addEventListener('pointerdown', e => {
    if (e.button !== 0 || g.drag) return;
    const btn = e.target.closest('button');
    if (!btn || btn.parentElement !== track || btn.disabled) return;
    // Sig'magan filtr kapsulasi yonga aylanadi — u yerda surish aylantirishga tegishli
    if (track.classList.contains('is-scrollable')) return;
    g.drag = { id: e.pointerId, startX: e.clientX, moved: false, over: null };
    if (g.active && !_reducedMotion?.matches) {
      clearTimeout(g.dropTimer);
      thumb.classList.add('is-lifted');
    }
  });
  track.addEventListener('pointermove', e => {
    const drag = g.drag;
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.moved) {
      if (Math.abs(e.clientX - drag.startX) < GLASS_DRAG_PX) return;
      drag.moved = true;
      track.setPointerCapture(e.pointerId);
      thumb.classList.add('is-lifted', 'is-dragging');
      track.classList.add('has-active');
    }
    moveGlassLens(track, e.clientX);
  });
  track.addEventListener('pointerup', e => { if (g.drag?.id === e.pointerId) endGlassDrag(track, false); });
  track.addEventListener('pointercancel', e => { if (g.drag?.id === e.pointerId) endGlassDrag(track, true); });
  track.addEventListener('lostpointercapture', e => { if (g.drag?.id === e.pointerId) endGlassDrag(track, true); });
  track.addEventListener('click', e => {
    if (g.suppressClick && e.isTrusted) {
      e.stopPropagation();
      e.preventDefault();
    }
  }, true);
}

document.querySelectorAll('.segmented, .nav-sections').forEach(initGlassTrack);


// ==========================================
// PASTGA TORTIB YANGILASH (bosh sahifa: telefon/planshetda barmoq, kompyuterda g'ildirak/touchpad)
// ==========================================
// Sahifa eng tepada turganda barmoq pastga tortilsa navbar ostidan brend "kapsulasi" chiqadi: loyiha logotipi (atrofida
// tortilgan sari to'ladigan halqa) va nomi. PTR_THRESHOLD dan ko'p tortib qo'yib yuborilsa refreshAll() — balans,
// hamyonlar, operatsiyalar serverdan qayta yuklanadi (sahifa qayta ochilmaydi).
// Logotip va nom navbardagi brenddan olinadi (.brand-badge-box, .brand-title) — loyiha nomi/logotipi o'zgarsa bu ham
// o'zi o'zgaradi. Brauzerning o'z "tortib yangilash"i style.css da o'chirilgan: overscroll-behavior-y
const PTR_THRESHOLD = 70;
const PTR_MAX = 110;
const PTR_DONE_MS = 450;  // tugagach halqa shuncha vaqt to'liq turadi — "yangilandi" degani
const _ptr = { el: null, startY: null, dist: 0, busy: false };

function _ptrIndicator() {
  if (!_ptr.el) {
    const name = document.querySelector('.brand-title')?.textContent.trim() || document.title.split('—')[0].trim();
    _ptr.el = document.createElement('div');
    _ptr.el.className = 'ptr-indicator';
    _ptr.el.setAttribute('aria-hidden', 'true');
    _ptr.el.innerHTML = `
      <span class="ptr-logo">
        <span class="brand-badge-box"></span>
        <svg class="ptr-ring" viewBox="0 0 36 36"><circle cx="18" cy="18" r="17" pathLength="100"/></svg>
      </span>
      <span class="ptr-name" data-no-i18n>${escapeHtml(name)}</span>`;
    document.body.appendChild(_ptr.el);
  }
  return _ptr.el;
}

// Faqat bosh sahifada: bo'lim sahifasi, oyna yoki tafsilot ochiq bo'lsa ularning o'z aylantirishi ishlaydi
function _ptrAllowed() {
  return !_ptr.busy && window.scrollY <= 0
    && !!document.getElementById('mainApp')?.offsetParent
    && !document.getElementById('txPageOverlay')?.classList.contains('open')
    && !_activeDialogLayer();
}

function _ptrReset() {
  _ptr.startY = null;
  _ptr.dist = 0;
  if (!_ptr.el) return;
  _ptr.el.classList.remove('pulling', 'ready');
  _ptr.el.style.setProperty('--ptr', 0);
  _ptr.el.style.setProperty('--p', 0);
}

document.addEventListener('touchstart', (e) => {
  _ptr.startY = e.touches.length === 1 && _ptrAllowed() ? e.touches[0].clientY : null;
}, { passive: true });

// Kapsulani "dist" px ga tushiradi (barmoq ham, g'ildirak ham shu orqali)
function _ptrSetDist(dist) {
  _ptr.dist = Math.min(PTR_MAX, Math.max(0, dist));
  const el = _ptrIndicator();
  el.classList.add('pulling');
  el.classList.toggle('ready', _ptr.dist >= PTR_THRESHOLD);
  el.style.setProperty('--ptr', _ptr.dist);
  el.style.setProperty('--p', Math.min(100, Math.round(_ptr.dist / PTR_THRESHOLD * 100)));
}

document.addEventListener('touchmove', (e) => {
  if (_ptr.startY === null) return;
  const dy = e.touches[0].clientY - _ptr.startY;
  if (dy <= 0 || window.scrollY > 0) { _ptrReset(); return; }
  // Barmoqdan sekinroq ergashadi — tortish "og'ir" seziladi, tasodifan yangilanib ketmaydi
  _ptrSetDist(dy * 0.5);
}, { passive: true });

function _ptrRelease() {
  if (_ptr.startY === null) return;
  _ptrFinish();
}

// Qo'yib yuborildi (barmoq ko'tarildi yoki g'ildirak to'xtadi): yetarli tortilgan bo'lsa yangilaydi
async function _ptrFinish() {
  const go = _ptr.dist >= PTR_THRESHOLD;
  _ptrReset();
  if (go) await _ptrRefresh();
}

// refreshAll() + kapsula animatsiyasi. Tortib yangilash va navbardagi "Moliya" (goHome) ishlatadi;
// yangilanish ketayotgan paytda qayta bosilsa ikkinchi so'rov yuborilmaydi
async function _ptrRefresh() {
  if (_ptr.busy) return;
  const el = _ptrIndicator();
  _ptr.busy = true;
  el.classList.add('refreshing');
  try {
    await refreshAll();
  } catch (err) {
    console.error('Pull-to-refresh failed:', err);
  } finally {
    el.classList.replace('refreshing', 'done');
    await new Promise(resolve => setTimeout(resolve, PTR_DONE_MS));
    el.classList.remove('done');
    _ptr.busy = false;
  }
}
document.addEventListener('touchend', _ptrRelease);
document.addEventListener('touchcancel', _ptrReset);

// Kompyuter (sichqoncha g'ildiragi, touchpad): sahifa eng tepada turganda yana yuqoriga aylantirish — barmoq bilan
// tortishning o'zi. Harakat tepada BOSHLANGAN bo'lishi shart: pastdan aylantirib kelib tepaga urilgan foydalanuvchida
// tasodifan yangilanmasin. G'ildirak PTR_WHEEL_IDLE_MS tinch tursa — "qo'yib yuborildi"
const PTR_WHEEL_IDLE_MS = 260;
const PTR_WHEEL_RATE = 0.25;  // 1 px aylantirish → 0.25 px tortish: odatiy sichqonchada ~3 "chiq", touchpadda ravon
const _ptrWheel = { active: false, lastAt: 0, timer: null };

document.addEventListener('wheel', (e) => {
  const now = performance.now();
  const fresh = now - _ptrWheel.lastAt > PTR_WHEEL_IDLE_MS;
  _ptrWheel.lastAt = now;
  if (fresh) _ptrWheel.active = e.deltaY < 0 && !e.ctrlKey && _ptrAllowed();
  if (!_ptrWheel.active) return;
  if (e.deltaY > 0 || window.scrollY > 0) {  // pastga burildi — bekor
    _ptrWheel.active = false;
    clearTimeout(_ptrWheel.timer);
    _ptrReset();
    return;
  }
  const px = e.deltaMode === 1 ? e.deltaY * 40 : e.deltaMode === 2 ? e.deltaY * window.innerHeight : e.deltaY;
  _ptrSetDist(_ptr.dist - px * PTR_WHEEL_RATE);
  clearTimeout(_ptrWheel.timer);
  _ptrWheel.timer = setTimeout(() => { _ptrWheel.active = false; _ptrFinish(); }, PTR_WHEEL_IDLE_MS);
}, { passive: true });
