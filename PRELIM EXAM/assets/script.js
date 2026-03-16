// Scroll reveal animation
const reveals = document.querySelectorAll(".reveal");

function revealOnScroll() {
  const windowHeight = window.innerHeight;
  const revealPoint = 100;

  reveals.forEach(section => {
    const sectionTop = section.getBoundingClientRect().top;

    if (sectionTop < windowHeight - revealPoint) {
      section.classList.add("active");
    }
  });
}

window.addEventListener("scroll", revealOnScroll);
revealOnScroll();

const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const finalScoreElement = document.getElementById('finalScore');
        const gameOverScreen = document.getElementById('gameOverScreen');

        const TILE_SIZE = 20;
        const GRID_WIDTH = 25;
        const GRID_HEIGHT = 25;
        const GAME_SPEED = 100;

        let snake = [];
        let food = {};
        let direction = 'RIGHT';
        let nextDirection = 'RIGHT';
        let running = false;
        let gameOver = false;
        let score = 0;
        let gameLoop = null;

        function init() {
            canvas.width = GRID_WIDTH * TILE_SIZE;
            canvas.height = GRID_HEIGHT * TILE_SIZE;
            setupMobileControls();
            startGame();
        }

        function setupMobileControls() {
            const btnUp = document.getElementById('btnUp');
            const btnDown = document.getElementById('btnDown');
            const btnLeft = document.getElementById('btnLeft');
            const btnRight = document.getElementById('btnRight');

            // Prevent default touch behavior
            [btnUp, btnDown, btnLeft, btnRight].forEach(btn => {
                btn.addEventListener('touchstart', (e) => e.preventDefault());
            });

            btnUp.addEventListener('click', () => {
                if (running && direction !== 'DOWN') nextDirection = 'UP';
            });

            btnDown.addEventListener('click', () => {
                if (running && direction !== 'UP') nextDirection = 'DOWN';
            });

            btnLeft.addEventListener('click', () => {
                if (running && direction !== 'RIGHT') nextDirection = 'LEFT';
            });

            btnRight.addEventListener('click', () => {
                if (running && direction !== 'LEFT') nextDirection = 'RIGHT';
            });

            // Touch support for better mobile experience
            btnUp.addEventListener('touchstart', (e) => {
                if (running && direction !== 'DOWN') nextDirection = 'UP';
            });

            btnDown.addEventListener('touchstart', (e) => {
                if (running && direction !== 'UP') nextDirection = 'DOWN';
            });

            btnLeft.addEventListener('touchstart', (e) => {
                if (running && direction !== 'RIGHT') nextDirection = 'LEFT';
            });

            btnRight.addEventListener('touchstart', (e) => {
                if (running && direction !== 'LEFT') nextDirection = 'RIGHT';
            });
        }

        function startGame() {
            snake = [
                { x: 5, y: 5 },
                { x: 4, y: 5 },
                { x: 3, y: 5 }
            ];
            
            direction = 'RIGHT';
            nextDirection = 'RIGHT';
            score = 0;
            gameOver = false;
            running = true;
            
            updateScore();
            gameOverScreen.classList.remove('show');
            spawnFood();
            
            if (gameLoop) clearInterval(gameLoop);
            gameLoop = setInterval(update, GAME_SPEED);
        }

        function spawnFood() {
            let validPosition = false;
            while (!validPosition) {
                food = {
                    x: Math.floor(Math.random() * GRID_WIDTH),
                    y: Math.floor(Math.random() * GRID_HEIGHT)
                };
                validPosition = !snake.some(segment => 
                    segment.x === food.x && segment.y === food.y
                );
            }
        }

        function update() {
            if (!running) return;

            direction = nextDirection;
            const head = { ...snake[0] };

            switch (direction) {
                case 'UP': head.y--; break;
                case 'DOWN': head.y++; break;
                case 'LEFT': head.x--; break;
                case 'RIGHT': head.x++; break;
            }

            // Check wall collision
            if (head.x < 0 || head.x >= GRID_WIDTH || 
                head.y < 0 || head.y >= GRID_HEIGHT) {
                endGame();
                return;
            }

            // Check self collision
            if (snake.some(segment => segment.x === head.x && segment.y === head.y)) {
                endGame();
                return;
            }

            snake.unshift(head);

            // Check if food is eaten
            if (head.x === food.x && head.y === food.y) {
                score += 10;
                updateScore();
                spawnFood();
            } else {
                snake.pop();
            }

            draw();
        }

        function draw() {
            // Clear canvas
            ctx.fillStyle = '#9bbc0f';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw food
            ctx.fillStyle = '#306230';
            ctx.fillRect(
                food.x * TILE_SIZE,
                food.y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE
            );

            // Draw snake
            snake.forEach((segment, index) => {
                ctx.fillStyle = index === 0 ? '#0f380f' : '#306230';
                ctx.fillRect(
                    segment.x * TILE_SIZE,
                    segment.y * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE
                );
            });
        }

        function endGame() {
            running = false;
            gameOver = true;
            clearInterval(gameLoop);
            finalScoreElement.textContent = score;
            gameOverScreen.classList.add('show');
        }

        function updateScore() {
            scoreElement.textContent = score;
        }

        function restartGame() {
            startGame();
        }

        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (gameOver && e.code === 'Space') {
                restartGame();
                return;
            }

            if (!running) return;

            switch (e.key) {
                case 'ArrowUp':
                case 'w':
                case 'W':
                    if (direction !== 'DOWN') nextDirection = 'UP';
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    if (direction !== 'UP') nextDirection = 'DOWN';
                    e.preventDefault();
                    break;
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    if (direction !== 'RIGHT') nextDirection = 'LEFT';
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    if (direction !== 'LEFT') nextDirection = 'RIGHT';
                    e.preventDefault();
                    break;
            }
        });

        // Start the game when page loads
        init();