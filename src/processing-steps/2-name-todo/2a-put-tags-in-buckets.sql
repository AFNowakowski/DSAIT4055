UPDATE Tags
SET hl_IsStableBucket = TRUE
WHERE TagName in (
                  'c',
                  'regex',
                  'sql',
                  'sorting',
                  'algorithm',
                  'math',
                  'bash',
                  'recursion',
                  'dynamic-programming',
                  'data-structures'
    );

UPDATE Tags
SET hl_IsStableBucket = FALSE
WHERE TagName in (
                  'node.js',
                  'npm',
                  'angularjs',
                  'reactjs',
                  'webpack',
                  'vue.js',
                  'react-native',
                  'flutter',
                  'angular',
                  'rust'
    );

ALTER TABLE Tags
MODIFY COLUMN hl_isStableBucket TINYINT(1) NOT NULL;


