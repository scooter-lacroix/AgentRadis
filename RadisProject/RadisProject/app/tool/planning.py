121|    async def run(self, **kwargs) -> Dict[str, Any]:
122|        """
123|        Run the planning tool with the given task or command.
124|        
125|        This method serves as the main entry point for the PlanningTool and supports
126|        both positional arguments (direct task specification) and keyword arguments
127|        (command-based approach).
128|        
129|        Args:
130|            **kwargs: Keyword arguments:
131|                task: The task description for plan creation
132|                command: The planning command to execute
133|                steps: List of steps for manual plan creation
134|                plan_id: ID of an existing plan to operate on
135|                validate: Whether to validate the generated plan
136|                reset: Whether to reset the current plan state
137|                verbose: Whether to display verbose output
138|        
139|        Returns:
140|            Dict[str, Any]: A dictionary containing the result of the operation.
141|        
142|        Raises:
143|            PlanningError: If an error occurs during planning operations.
144|        """
145|        command = kwargs.get("command", "create" if kwargs.get("task") else None)
146|        self.verbose = kwargs.get("verbose", self.verbose)
147|        
148|        try:
149|            if command == "create" or kwargs.get("task"):
150|                # Create a new plan either from a task description or from provided steps
151|                task = kwargs.get("task")
152|                steps = kwargs.get("steps", None)
153|                
154|                if task and not steps:
155|                    # Generate a plan based on the task description
156|                    plan = await self._generate_plan_with_agent(task)
157|                    self.current_plan = plan
158|                    self.current_plan_id = str(uuid.uuid4())
159|                    self.current_step_index = 0
160|                    await self._save_plan(self.current_plan_id, plan)
161|                    
162|                    result = {
163|                        "status": "success",
164|                        "message": f"Plan created with ID: {self.current_plan_id}",
165|                        "plan_id": self.current_plan_id,
166|                        "plan": plan
167|                    }
168|                    
169|                    if kwargs.get("validate", False):
170|                        validation_result = await self._validate_plan(plan)
171|                        result["validation"] = validation_result
172|                    
173|                    return result
174|                    
175|                elif steps:
176|                    # Create a plan from provided steps
177|                    plan = steps
178|                    self.current_plan = plan
179|                    self.current_plan_id = str(uuid.uuid4())
180|                    self.current_step_index = 0
181|                    await self._save_plan(self.current_plan_id, plan)
182|                    
183|                    return {
184|                        "status": "success",
185|                        "message": f"Plan created with ID: {self.current_plan_id}",
186|                        "plan_id": self.current_plan_id,
187|                        "plan": plan
188|                    }
189|                else:
190|                    raise PlanningError("No task description or steps provided for plan creation")
191|            
192|            elif command == "load":
193|                # Load an existing plan
194|                plan_id = kwargs.get("plan_id")
195|                if not plan_id:
196|                    raise PlanningError("No plan_id provided for loading")
197|                
198|                plan = await self._load_plan(plan_id)
199|                self.current_plan = plan
200|                self.current_plan_id = plan_id
201|                self.current_step_index = 0
202|                
203|                return {
204|                    "status": "success",
205|                    "message": f"Plan loaded with ID: {plan_id}",
206|                    "plan_id": plan_id,
207|                    "plan": plan
208|                }
209|            
210|            elif command == "execute":
211|                # Execute the current plan or a specified plan
212|                plan_id = kwargs.get("plan_id")
213|                if plan_id and plan_id != self.current_plan_id:
214|                    plan = await self._load_plan(plan_id)
215|                    self.current_plan = plan
216|                    self.current_plan_id = plan_id
217|                    self.current_step_index = 0
218|                
219|                if not self.current_plan:
220|                    raise PlanningError("No current plan to execute")
221|                
222|                return await self._execute_plan(self.current_plan)
223|            
224|            elif command == "execute_step":
225|                # Execute the next step in the current plan
226|                if not self.current_plan:
227|                    raise PlanningError("No current plan to execute step from")
228|                
229|                if self.current_step_index >= len(self.current_plan):
230|                    return {
231|                        "status": "complete", 
232|                        "message": "Plan execution completed",
233|                        "plan_id": self.current_plan_id
234|                    }
235|                
236|                step_result = await self._execute_step(self.current_plan[self.current_step_index])
237|                self.current_step_index += 1
238|                
239|                return {
240|                    "status": "success" if step_result["status"] == "success" else "error",
241|                    "message": f"Executed step {self.current_step_index} of {len(self.current_plan)}",
242|                    "step_index": self.current_step_index - 1,
243|                    "step_result": step_result,
244|                    "next_step_index": self.current_step_index if self.current_step_index < len(self.current_plan) else None,
245|                    "next_step": self.current_plan[self.current_step_index] if self.current_step_index < len(self.current_plan) else None,
246|                    "plan_id": self.current_plan_id
247|                }
248|            
249|            elif command == "validate":
250|                # Validate the current plan or a specified plan
251|                plan_id = kwargs.get("plan_id")
252|                if plan_id and plan_id != self.current_plan_id:
253|                    plan = await self._load_plan(plan_id)
254|                else:
255|                    plan = self.current_plan
256|                
257|                if not plan:
258|                    raise PlanningError("No plan to validate")
259|                
260|                validation_result = await self._validate_plan(plan)
261|                
262|                return {
263|                    "status": "success",
264|                    "message": "Plan validation completed",
265|                    "validation": validation_result,
266|                    "plan_id": self.current_plan_id
267|                }
268|            
269|            elif command == "list":
270|                # List all available plans
271|                plans = await self._list_plans()
272|                
273|                return {
274|                    "status": "success",
275|                    "message": f"Found {len(plans)} plans",
276|                    "plans": plans
277|                }
278|            
279|            elif command == "get_status":
280|                # Get the current status of plan execution
281|                if not self.current_plan:
282|                    return {
283|                        "status": "no_plan",
284|                        "message": "No current plan"
285|                    }
286|                
287|                return {
288|                    "status": "in_progress",
289|                    "message": f"Plan execution in progress: step {self.current_step_index} of {len(self.current_plan)}",
290|                    "plan_id": self.current_plan_id,
291|                    "current_step_index": self.current_step_index,
292|                    "total_steps": len(self.current_plan),
293|                    "current_step": self.current_plan[self.current_step_index] if self.current_step_index < len(self.current_plan) else None,
294|                    "failed_step": self.failed_step
295|                }
296|            
297|            elif command == "reset":
298|                # Reset the current plan execution state
299|                self.current_step_index = 0
300|                self.failed_step = None
301|                
302|                return {
303|                    "status": "success",
304|                    "message": "Plan execution state reset",
305|                    "plan_id": self.current_plan_id
306|                }
307|            
308|            elif command == "delete":
309|                # Delete a plan
310|                plan_id = kwargs.get("plan_id")
311|                if not plan_id:
312|                    raise PlanningError("No plan_id provided for deletion")
313|                
314|                await self._delete_plan(plan_id)
315|                
316|                if plan_id == self.current_plan_id:
317|                    self.current_plan = None
318|                    self.current_plan_id = None
319|                    self.current_step_index = 0
320|                    self.failed_step = None
321|                
322|                return {
323|                    "status": "success",
324|                    "message": f"Plan with ID {plan_id} deleted"
325|                }
326|            
327|            else:
328|                raise PlanningError(f"Unknown command: {command}")
329|        
330|        except Exception as e:
331|            error_message = str(e)
332|            stack_trace = traceback.format_exc()
333|            
334|            if isinstance(e, PlanningError):
335|                if self.verbose:
336|                    display(f"PlanningError: {error_message}", "error")
337|                return {
338|                    "status": "error",
339|                    "error_type": "PlanningError",
340|                    "message": error_message
341|                }
342|            else:
343|                if self.verbose:
344|                    display(f"Error during planning operation: {error_message}", "error")
345|                    display(stack_trace, "error")
346|                return {
347|                    "status": "error",
348|                    "error_type": type(e).__name__,
349|                    "message": error_message,
350|                    "stack_trace": stack_trace
351|                }
352|
353|    async def _generate_plan_with_agent(self, task: str) -> List[str]:
354|        """
355|        Generate a plan using an AI agent.
356|        
357|        Args:
358|            task: The task description to create a plan for
359|            
360|        Returns:
361|            List[str]: A list of plan steps
362|            
363|        Raises:
364|            PlanningError: If plan generation fails
365|        """
366|        if not self.agent:
367|            return await self._generate_basic_plan(task)
368|        
369|        try:
370|            if self.verbose:
371|                display(f"Generating plan for task: {task}", "info")
372|                
373|            # Create prompt for the agent
374|            prompt = f"""
375|            Create a detailed step-by-step plan for accomplishing the following task:
376|            
377|            {task}
378|            
379|            Format the response as a JSON array of steps:
380|            [
381|                "First step with detailed instructions",
382|                "Second step with detailed instructions",
383|                ...
384|            ]
385|            
386|            Make sure to:
387|            1. Break down complex operations into clear, manageable steps
388|            2. Include all necessary commands or actions for each step
389|            3. Be specific about tools and techniques to use
390|            4. Order the steps logically
391|            5. Don't skip important prerequisites
392|            """
393|            
394|            # Generate plan with the agent
395|            response = await self.agent.run(prompt)
396|            
397|            # Extract the plan steps from the response
398|            if isinstance(response, dict):
399|                response_text = response.get("output", response.get("response", ""))
400|            else:
401|                response_text = str(response)
402|                
403|            # Try to extract JSON
404|            json_start = response_text.find("[")
405|            json_end = response_text.rfind("]") + 1
406|            
407|            if json_start >= 0 and json_end > json_start:
408|                try:
409|                    plan_json = response_text[json_start:json_end]
410|                    plan = json.loads(plan_json)
411|                    if isinstance(plan, list) and all(isinstance(step, str) for step in plan):
412|                        if self.verbose:
413|                            display(f"Successfully generated plan with {len(plan)} steps", "info")
414|                        return plan
415|                except json.JSONDecodeError:
416|                    if self.verbose:
417|                        display("Failed to parse JSON from agent response", "warning")
418|                        
419|            # Try regex-based extraction as fallback
420|            steps = re.findall(r'"([^"]+)"', response_text)
421|            if steps and len(steps) > 1:
422|                if self.verbose:
423|                    display(f"Extracted plan with {len(steps)} steps using regex", "info")
424|                return steps
425|            
426|            # If we get here, we couldn't extract a proper plan
427|            if self.verbose:
428|                display("Failed to extract plan from agent response, falling back to basic plan", "warning")
429|            return await self._generate_basic_plan(task)
430|            
431|        except Exception as e:
432|            if self.verbose:
433|                display(f"Error generating plan with agent: {str(e)}", "error")
434|            # Fall back to basic plan
435|            return await self._generate_basic_plan(task)
436|
437|    async def _generate_basic_plan(self, task: str) -> List[str]:
438|        """
439|        Generate a basic plan without using an agent.
440|        
441|        Args:
442|            task: The task description to create a plan for
443|            
444
