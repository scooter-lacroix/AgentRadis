import os
import asyncio
import shutil
from typing import List, ClassVar, Dict, Any

from app.agent.toolcall import ToolCallAgent
from app.tool import StrReplaceEditor, WebSearch, Terminate, BaseTool, ToolCollection
from app.schema import AgentMemory, Message, Role, AgentState

class TestBench:
    """Test bench for validating AgentRadis components"""
    
    def __init__(self):
        self.test_results = []
        self.test_dir = "test_outputs"
        
        # Create test directory if it doesn't exist
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
    
    async def run_tests(self):
        """Run all component tests"""
        await self.test_str_replace_editor()
        await self.test_tool_collection()
        await self.test_web_search()
        self.print_summary()
    
    def add_result(self, test_name, status, message=None):
        """Add a test result"""
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
        print(f"[{status.upper()}] {test_name} - {message if message else ''}")
    
    async def test_str_replace_editor(self):
        """Test the StrReplaceEditor tool"""
        test_name = "StrReplaceEditor"
        try:
            # Create a test file
            test_file = os.path.join(self.test_dir, "str_replace_test.txt")
            with open(test_file, "w") as f:
                f.write("This is a test file\nwith multiple lines\nto test the string replace editor.")
            
            # Initialize the tool
            editor = StrReplaceEditor()
            
            # Test basic string replacement
            result = await editor.run(
                file_path=test_file,
                search="test",
                replace="sample"
            )
            
            # Verify replacement was successful
            if result["status"] == "success" and result["replacements"] > 0:
                with open(test_file, "r") as f:
                    content = f.read()
                if "sample" in content and "test" not in content:
                    self.add_result(test_name, "pass", "Basic string replacement successful")
                else:
                    self.add_result(test_name, "fail", f"Basic replacement verification failed: {content}")
            else:
                self.add_result(test_name, "fail", f"Basic replacement failed: {result}")
            
            # Clean up
            await editor.cleanup()
            
        except Exception as e:
            self.add_result(test_name, "error", f"Exception: {str(e)}")
    
    async def test_tool_collection(self):
        """Test the ToolCollection implementation including to_params method"""
        test_name = "ToolCollection"
        try:
            # Create a collection with several tools
            tools = ToolCollection(
                StrReplaceEditor(),
                WebSearch(),
                Terminate()
            )
            
            # Test to_params method
            params = tools.to_params()
            
            # Verify the params have the expected OpenAI function call format
            if isinstance(params, list) and len(params) == 3:
                if all(
                    isinstance(p, dict) and
                    p.get("type") == "function" and
                    "function" in p and
                    isinstance(p["function"], dict) and
                    "name" in p["function"] and
                    "parameters" in p["function"]
                    for p in params
                ):
                    self.add_result(test_name, "pass", "to_params method returns correctly formatted OpenAI function calls")
                else:
                    self.add_result(test_name, "fail", "Invalid format in to_params output")
            else:
                self.add_result(test_name, "fail", f"Unexpected result from to_params: {params}")
                
        except Exception as e:
            self.add_result(test_name, "error", f"Exception: {str(e)}")
    
    async def test_web_search(self):
        """Test WebSearch tool including proper session cleanup"""
        test_name = "WebSearch"
        try:
            # Initialize the search tool
            search = WebSearch()
            
            # Perform a simple search
            result = await search.run(
                query="python programming",
                engine="google",
                num_results=2
            )
            
            # Verify search was successful
            if result["status"] == "success":
                self.add_result(test_name, "pass", "Search execution successful")
            else:
                self.add_result(test_name, "fail", f"Search failed: {result}")
            
            # Test cleanup method to ensure sessions are properly closed
            await search.cleanup()
            self.add_result(test_name + " Cleanup", "pass", "Cleanup completed without errors")
                
        except Exception as e:
            self.add_result(test_name, "error", f"Exception: {str(e)}")
    
    def print_summary(self):
        """Print a summary of all test results"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "pass")
        failed = sum(1 for r in self.test_results if r["status"] == "fail")
        errors = sum(1 for r in self.test_results if r["status"] == "error")
        
        print("\n==== TEST SUMMARY ====")
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print("=====================")
    
    def cleanup(self):
        """Clean up any test artifacts"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

async def main():
    """Run the test bench"""
    test_bench = TestBench()
    try:
        await test_bench.run_tests()
    finally:
        test_bench.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 