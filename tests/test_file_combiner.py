"""Enhanced test suite for file combiner functionality.

This module provides comprehensive testing of the file combiner processor,
including complex scenarios, multi-language support, and error cases.

Path: tests/test_file_combiner.py
"""

from pathlib import Path
import tempfile
import textwrap
from typing import Generator, Any
import pytest

from pyweaver.processors import (
    FileCombinerProcessor,
    combine_files,
    ContentMode,
    FileSectionConfig
)

@pytest.fixture
def mixed_source_files() -> Generator[Path, Any, None]:
    """Create a mixed-language source directory for testing.

    This fixture creates files in multiple languages with various
    comment styles and documentation patterns.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create React component with TypeScript
        component_file = tmp_path / "UserList.tsx"
        component_file.write_text(textwrap.dedent('''
            /**
             * User list component with filtering and pagination.
             *
             * @component
             * @example
             * ```tsx
             * <UserList users={users} onSelect={handleSelect} />
             * ```
             */

            import React, { useState } from 'react';

            // Interface for user data
            interface User {
                id: number;
                name: string;
                email: string;
                active: boolean;
            }

            interface UserListProps {
                users: User[];
                onSelect?: (user: User) => void;
            }

            // Component implementation
            const UserList: React.FC<UserListProps> = ({ users, onSelect }) => {
                const [filter, setFilter] = useState("");

                /* Filter users based on search text */
                const filteredUsers = users.filter(user =>
                    user.name.toLowerCase().includes(filter.toLowerCase())
                );

                return (
                    <div className="user-list">
                        {/* Search input */}
                        <input
                            type="text"
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            placeholder="Search users..."
                        />

                        {/* User list */}
                        <ul>
                            {filteredUsers.map(user => (
                                <li
                                    key={user.id}
                                    onClick={() => onSelect?.(user)}
                                >
                                    {user.name} ({user.email})
                                </li>
                            ))}
                        </ul>
                    </div>
                );
            };

            export default UserList;
        '''))

        # Create style file
        styles_file = tmp_path / "styles.scss"
        styles_file.write_text(textwrap.dedent('''
            /* Main styles for user interface */

            // Variables
            $primary-color: #007bff;
            $spacing: 1rem;

            .user-list {
                /* Container styles */
                padding: $spacing;

                input {
                    /* Search input styles */
                    width: 100%;
                    padding: $spacing * 0.5;
                    margin-bottom: $spacing;

                    // Focus state
                    &:focus {
                        outline-color: $primary-color;
                    }
                }

                ul {
                    /* List container */
                    list-style: none;
                    padding: 0;

                    li {
                        /* List items */
                        padding: $spacing * 0.5;
                        cursor: pointer;

                        /* Hover state */
                        &:hover {
                            background: lighten($primary-color, 45%);
                        }
                    }
                }
            }
        '''))

        # Create Python util file
        utils_file = tmp_path / "user_utils.py"
        utils_file.write_text(textwrap.dedent('''
            """Utility functions for user management.

            This module provides helper functions for processing and validating
            user data before display.
            """

            from typing import List, Dict, Any

            def validate_user(user_data: Dict[str, Any]) -> bool:
                """Validate user data structure.

                Args:
                    user_data: Dictionary containing user information

                Returns:
                    True if user data is valid
                """
                # Check required fields
                required = {'id', 'name', 'email'}
                if not all(field in user_data for field in required):
                    return False

                # Validate types
                return (
                    isinstance(user_data['id'], int) and
                    isinstance(user_data['name'], str) and
                    isinstance(user_data['email'], str)
                )

            def format_user_display(user_data: Dict[str, Any]) -> str:
                """Format user data for display.

                Args:
                    user_data: Dictionary containing user information

                Returns:
                    Formatted display string
                """
                # Format display string
                return f"{user_data['name']} ({user_data['email']})"
        '''))

        # Create Vue component
        vue_file = tmp_path / "UserDetail.vue"
        vue_file.write_text(textwrap.dedent('''
            <template>
              <div class="user-detail">
                <!-- User information display -->
                <div v-if="user" class="user-info">
                  <h2>{{ user.name }}</h2>
                  <p>{{ user.email }}</p>
                  <span :class="statusClass">
                    {{ user.active ? 'Active' : 'Inactive' }}
                  </span>
                </div>
                <p v-else>No user selected</p>
              </div>
            </template>

            <script>
            /**
             * Component for displaying detailed user information
             */
            export default {
                name: 'UserDetail',

                props: {
                    // User data to display
                    user: {
                        type: Object,
                        required: false,
                        default: null
                    }
                },

                computed: {
                    // Compute status class based on user state
                    statusClass() {
                        return {
                            'status': true,
                            'active': this.user?.active,
                            'inactive': !this.user?.active
                        }
                    }
                }
            }
            </script>

            <style lang="scss" scoped>
            /* Component styles */
            .user-detail {
                padding: 1rem;

                .user-info {
                    /* Information container */
                    border: 1px solid #ddd;
                    padding: 1rem;

                    .status {
                        /* Status indicator */
                        &.active {
                            color: green;
                        }

                        &.inactive {
                            color: red;
                        }
                    }
                }
            }
            </style>
        '''))

        yield tmp_path

def test_content_modes(mixed_source_files: Path):
    """Test different content processing modes."""
    output_file = mixed_source_files / "combined.txt"

    # Test each content mode
    for mode in ContentMode:
        combiner = FileCombinerProcessor(
            root_dir=mixed_source_files,
            output_file=output_file,
            patterns=["*.*"],
            content_mode=mode
        )

        result = combiner.process()
        assert result.success

        content = output_file.read_text()

        if mode == ContentMode.FULL:
            # Should include all comments and docstrings
            assert '"""Utility functions for user management."""' in content
            assert "// Variables" in content
            assert "/* Component styles */" in content

        elif mode == ContentMode.NO_COMMENTS:
            # Should include docstrings but not comments
            assert '"""Utility functions for user management."""' in content
            assert "// Variables" not in content
            assert "/* Component styles */" not in content

        elif mode == ContentMode.NO_DOCSTRINGS:
            # Should include comments but not docstrings
            assert '"""Utility functions for user management."""' not in content
            assert "// Variables" in content
            assert "/* Component styles */" in content

        elif mode == ContentMode.MINIMAL:
            # Should exclude both comments and docstrings
            assert '"""Utility functions for user management."""' not in content
            assert "// Variables" not in content
            assert "/* Component styles */" not in content

def test_section_formatting(mixed_source_files: Path):
    """Test section formatting configuration."""
    output_file = mixed_source_files / "combined.txt"

    # Create custom section config
    section_config = FileSectionConfig(
        enabled=True,
        header_template="### {path} ###",
        footer_template="\n# End of {path} #\n",
        include_empty_lines=False,
        remove_trailing_whitespace=True
    )

    combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=output_file,
        patterns=["*.*"],
        section_config=section_config
    )

    result = combiner.process()
    assert result.success

    content = output_file.read_text()

    # Verify section formatting
    assert "### UserList.tsx ###" in content
    assert "# End of UserList.tsx #" in content
    assert "### styles.scss ###" in content
    assert "# End of styles.scss #" in content

    # Verify empty line handling
    lines = content.splitlines()
    assert not any(line.isspace() for line in lines)
    assert not any(line.endswith(" ") for line in lines)

def test_preview_and_tree(mixed_source_files: Path):
    """Test preview functionality and tree generation."""
    combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=mixed_source_files / "combined.txt",
        patterns=["*.*"],
        generate_tree=True
    )

    # Test preview
    preview = combiner.preview()
    assert isinstance(preview, str)
    assert "UserList.tsx" in preview
    assert "styles.scss" in preview
    assert "user_utils.py" in preview

    # Test tree generation
    tree = combiner.generate_tree()
    assert isinstance(tree, str)
    assert "UserList.tsx" in tree
    assert "styles.scss" in tree
    assert "user_utils.py" in tree

    # Verify tree structure indicators
    assert "├──" in tree or "└──" in tree

def test_pattern_matching(mixed_source_files: Path):
    """Test pattern-based file selection."""
    output_file = mixed_source_files / "combined.txt"

    # Test TypeScript files
    ts_combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=output_file,
        patterns=["*.tsx"]
    )
    result = ts_combiner.process()
    assert result.success
    content = output_file.read_text()
    assert "UserList" in content
    assert ".user-list" not in content  # SCSS content
    assert "validate_user" not in content  # Python content

    # Test style files
    style_combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=output_file,
        patterns=["*.scss", "*.css"]
    )
    result = style_combiner.process()
    assert result.success
    content = output_file.read_text()
    assert ".user-list" in content
    assert "UserList" not in content  # TypeScript content
    assert "validate_user" not in content  # Python content

def test_large_file_handling(mixed_source_files: Path):
    """Test handling of large files."""
    # Create a large file
    large_file = mixed_source_files / "large.ts"
    with large_file.open('w') as f:
        # Write 100K lines
        for i in range(100000):
            f.write(f"// Line {i}\n")
            f.write(f"const value_{i} = {i};\n")

    output_file = mixed_source_files / "combined.txt"
    combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=output_file,
        patterns=["large.ts"]
    )

    result = combiner.process()
    assert result.success

    # Verify content was processed correctly
    content = output_file.read_text()
    assert "Line 0" in content
    assert "Line 99999" in content
    assert "const value_0 = 0" in content

def test_error_handling(mixed_source_files: Path):
    """Test error handling scenarios."""
    output_file = mixed_source_files / "combined.txt"

    # Test with non-existent directory
    with pytest.raises(Exception):
        FileCombinerProcessor(
            root_dir=mixed_source_files / "nonexistent",
            output_file=output_file
        )

    # Test with invalid pattern
    with pytest.raises(Exception):
        FileCombinerProcessor(
            root_dir=mixed_source_files,
            output_file=output_file,
            patterns=["[invalid"]
        )

    # Test with unreadable file
    bad_file = mixed_source_files / "unreadable.py"
    bad_file.write_text("print('test')")
    bad_file.chmod(0o000)  # Remove read permissions

    combiner = FileCombinerProcessor(
        root_dir=mixed_source_files,
        output_file=output_file
    )
    result = combiner.process()

    assert not result.success
    assert len(result.errors) > 0
    assert any("permission" in str(error).lower() for error in result.errors)

def test_convenience_function(mixed_source_files: Path):
    """Test the combine_files convenience function."""
    output_file = mixed_source_files / "combined.txt"

    result = combine_files(
        mixed_source_files,
        output_file,
        patterns=["*.tsx", "*.vue"],
        remove_comments=True
    )

    assert result.success
    assert result.files_processed == 2  # UserList.tsx and UserDetail.vue

    content = output_file.read_text()
    assert "UserList" in content
    assert "UserDetail" in content
    assert "// Variables" not in content  # Comments should be removed

if __name__ == "__main__":
    pytest.main([__file__])