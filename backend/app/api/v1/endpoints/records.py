"""
Record API endpoints.

Handles record querying, retrieval, updates, deletion, and bulk operations
with advanced filtering, sorting, and pagination.
"""

import logging
from typing import List, Optional, Any, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import select, func, and_, or_, cast, String, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models.user import User
from app.models.record import Record
from app.models.dataset import Dataset
from app.schemas.record import (
    RecordResponse,
    RecordListResponse,
    RecordFilter,
    RecordSort,
    FilterOperator,
    SortDirection,
    RecordCreate,
    RecordStats
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/datasets/{dataset_id}/records",
    response_model=RecordListResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def query_records(
    dataset_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    filters: Optional[str] = Query(None, description="JSON string of filters"),
    sort_column: Optional[str] = Query(None, description="Column to sort by"),
    sort_direction: Optional[SortDirection] = Query(SortDirection.ASC, description="Sort direction"),
    only_valid: Optional[bool] = Query(None, description="Filter by validation status"),
    search: Optional[str] = Query(None, description="Search across all text fields"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Query records with advanced filtering, sorting, and pagination.
    
    **Filter Operators:**
    - `eq` - Equals
    - `ne` - Not equals
    - `gt` - Greater than
    - `gte` - Greater than or equal
    - `lt` - Less than
    - `lte` - Less than or equal
    - `contains` - Contains substring (case-insensitive)
    - `starts_with` - Starts with
    - `ends_with` - Ends with
    - `in` - In list
    - `not_in` - Not in list
    - `is_null` - Is null
    - `is_not_null` - Is not null
    
    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset_stmt = select(Dataset).where(
            and_(
                Dataset.id == dataset_id,
                Dataset.organization_id == organization_id,
                Dataset.deleted_at.is_(None)
            )
        )
        dataset_result = await db.execute(dataset_stmt)
        dataset = dataset_result.scalar_one_or_none()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        # Build base query
        base_stmt = select(Record).where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id
            )
        )
        
        # Apply validation filter
        if only_valid is not None:
            base_stmt = base_stmt.where(Record.is_valid == only_valid)
        
        # Apply filters
        if filters:
            import json
            try:
                filter_list = json.loads(filters)
                for filter_def in filter_list:
                    filter_condition = _build_filter_condition(
                        filter_def.get('column'),
                        filter_def.get('operator'),
                        filter_def.get('value')
                    )
                    if filter_condition is not None:
                        base_stmt = base_stmt.where(filter_condition)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid filters JSON"
                )
        
        # Apply search
        if search:
            # Search across all text fields in the data JSONB column
            search_condition = cast(Record.data, String).ilike(f"%{search}%")
            base_stmt = base_stmt.where(search_condition)
        
        # Get total count
        count_stmt = select(func.count()).select_from(base_stmt.alias())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar()
        
        # Apply sorting
        if sort_column:
            if sort_direction == SortDirection.DESC:
                base_stmt = base_stmt.order_by(
                    Record.data[sort_column].desc().nulls_last()
                )
            else:
                base_stmt = base_stmt.order_by(
                    Record.data[sort_column].asc().nulls_last()
                )
        else:
            # Default sort by row_number
            base_stmt = base_stmt.order_by(Record.row_number.asc())
        
        # Apply pagination
        base_stmt = base_stmt.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(base_stmt)
        records = result.scalars().all()
        
        # Build response
        has_more = (skip + len(records)) < total
        
        logger.info(f"Queried {len(records)} records from dataset {dataset_id} (total: {total})")
        
        return RecordListResponse(
            total=total,
            skip=skip,
            limit=limit,
            records=[RecordResponse.from_orm(record) for record in records],
            has_more=has_more
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query records: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query records"
        )


@router.get(
    "/records/{record_id}",
    response_model=RecordResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get single record details.
    
    **Required Permission:** `data:view`
    """
    try:
        stmt = select(Record).where(
            and_(
                Record.id == record_id,
                Record.organization_id == organization_id
            )
        )
        
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record {record_id} not found"
            )
        
        return RecordResponse.from_orm(record)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve record"
        )


@router.put(
    "/records/{record_id}",
    response_model=RecordResponse,
    dependencies=[Depends(require_permission("data:edit"))]
)
async def update_record(
    record_id: UUID,
    data: Dict[str, Any] = Body(..., description="Updated record data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Update record data.
    
    Accepts a dictionary of column values to update.
    Re-runs validation if validation rules exist.
    
    **Required Permission:** `data:edit`
    """
    try:
        # Get record
        stmt = select(Record).where(
            and_(
                Record.id == record_id,
                Record.organization_id == organization_id
            )
        )
        
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record {record_id} not found"
            )
        
        # Update data
        record.data = data
        
        # Re-run validation if dataset schema exists
        validation_errors = []
        
        # Get dataset schema for validation
        if record.dataset and record.dataset.schema:
            schema = record.dataset.schema
            
            # Validate required fields
            if 'required_columns' in schema:
                for required_col in schema['required_columns']:
                    if required_col not in data or data[required_col] is None:
                        validation_errors.append({
                            'field': required_col,
                            'error': 'Required field is missing or null'
                        })
            
            # Validate data types if schema includes column types
            if 'columns' in schema:
                for col_name, col_info in schema['columns'].items():
                    if col_name in data and data[col_name] is not None:
                        expected_type = col_info.get('type')
                        value = data[col_name]
                        
                        # Basic type validation
                        if expected_type == 'integer' and not isinstance(value, (int, float)):
                            try:
                                int(value)
                            except (ValueError, TypeError):
                                validation_errors.append({
                                    'field': col_name,
                                    'error': f'Expected integer, got {type(value).__name__}'
                                })
                        
                        elif expected_type == 'float' and not isinstance(value, (int, float)):
                            try:
                                float(value)
                            except (ValueError, TypeError):
                                validation_errors.append({
                                    'field': col_name,
                                    'error': f'Expected float, got {type(value).__name__}'
                                })
        
        # Update validation status
        record.is_valid = len(validation_errors) == 0
        record.validation_errors = validation_errors if validation_errors else None
        
        await db.commit()
        await db.refresh(record)
        
        logger.info(f"User {current_user.id} updated record {record_id}")
        
        return RecordResponse.from_orm(record)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update record"
        )


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("data:delete"))]
)
async def delete_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Delete single record.
    
    Permanently removes the record from the database.
    
    **Required Permission:** `data:delete`
    """
    try:
        # Get record
        stmt = select(Record).where(
            and_(
                Record.id == record_id,
                Record.organization_id == organization_id
            )
        )
        
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record {record_id} not found"
            )
        
        # Delete record
        await db.delete(record)
        await db.commit()
        
        logger.info(f"User {current_user.id} deleted record {record_id}")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete record {record_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete record"
        )


@router.post(
    "/datasets/{dataset_id}/records/bulk",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_permission("data:edit"))]
)
async def bulk_record_operations(
    dataset_id: UUID,
    operations: List[Dict[str, Any]] = Body(
        ...,
        description="Array of operations to perform",
        examples=[{
            "operations": [
                {
                    "operation": "create",
                    "data": {"name": "John", "age": 30}
                },
                {
                    "operation": "update",
                    "record_id": "123e4567-e89b-12d3-a456-426614174000",
                    "data": {"age": 31}
                },
                {
                    "operation": "delete",
                    "record_id": "123e4567-e89b-12d3-a456-426614174001"
                }
            ]
        }]
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Bulk create, update, or delete records.
    
    **Operation Types:**
    - `create`: Create new record with data
    - `update`: Update existing record by ID with new data
    - `delete`: Delete record by ID
    
    **Required Permission:** `data:edit`
    
    Returns success/failure status for each operation.
    """
    try:
        # Verify dataset exists
        dataset_stmt = select(Dataset).where(
            and_(
                Dataset.id == dataset_id,
                Dataset.organization_id == organization_id,
                Dataset.deleted_at.is_(None)
            )
        )
        dataset_result = await db.execute(dataset_stmt)
        dataset = dataset_result.scalar_one_or_none()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        results = []
        success_count = 0
        failure_count = 0
        
        for i, operation in enumerate(operations):
            op_type = operation.get('operation')
            
            try:
                if op_type == 'create':
                    # Create new record
                    data = operation.get('data')
                    if not data:
                        raise ValueError("Missing 'data' field for create operation")
                    
                    # Get next row number
                    max_row_stmt = select(func.max(Record.row_number)).where(
                        Record.dataset_id == dataset_id
                    )
                    max_row_result = await db.execute(max_row_stmt)
                    max_row = max_row_result.scalar() or 0
                    
                    record = Record(
                        organization_id=organization_id,
                        dataset_id=dataset_id,
                        row_number=max_row + 1,
                        data=data,
                        is_valid=True,
                        validation_errors=None
                    )
                    
                    db.add(record)
                    await db.flush()
                    
                    results.append({
                        'index': i,
                        'operation': op_type,
                        'status': 'success',
                        'record_id': str(record.id)
                    })
                    success_count += 1
                
                elif op_type == 'update':
                    # Update existing record
                    record_id = operation.get('record_id')
                    data = operation.get('data')
                    
                    if not record_id:
                        raise ValueError("Missing 'record_id' field for update operation")
                    if not data:
                        raise ValueError("Missing 'data' field for update operation")
                    
                    # Get record
                    stmt = select(Record).where(
                        and_(
                            Record.id == UUID(record_id),
                            Record.organization_id == organization_id,
                            Record.dataset_id == dataset_id
                        )
                    )
                    result = await db.execute(stmt)
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        raise ValueError(f"Record {record_id} not found")
                    
                    record.data = data
                    
                    results.append({
                        'index': i,
                        'operation': op_type,
                        'status': 'success',
                        'record_id': record_id
                    })
                    success_count += 1
                
                elif op_type == 'delete':
                    # Delete record
                    record_id = operation.get('record_id')
                    
                    if not record_id:
                        raise ValueError("Missing 'record_id' field for delete operation")
                    
                    # Get record
                    stmt = select(Record).where(
                        and_(
                            Record.id == UUID(record_id),
                            Record.organization_id == organization_id,
                            Record.dataset_id == dataset_id
                        )
                    )
                    result = await db.execute(stmt)
                    record = result.scalar_one_or_none()
                    
                    if not record:
                        raise ValueError(f"Record {record_id} not found")
                    
                    await db.delete(record)
                    
                    results.append({
                        'index': i,
                        'operation': op_type,
                        'status': 'success',
                        'record_id': record_id
                    })
                    success_count += 1
                
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")
            
            except Exception as e:
                results.append({
                    'index': i,
                    'operation': op_type,
                    'status': 'failed',
                    'error': str(e)
                })
                failure_count += 1
                logger.warning(f"Bulk operation {i} failed: {e}")
        
        # Commit all changes
        await db.commit()
        
        logger.info(
            f"Bulk operations completed: {success_count} success, {failure_count} failed"
        )
        
        return {
            'total': len(operations),
            'success_count': success_count,
            'failure_count': failure_count,
            'results': results
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to perform bulk operations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operations"
        )


@router.get(
    "/datasets/{dataset_id}/records/stats",
    response_model=RecordStats,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_record_stats(
    dataset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get statistics about records in a dataset.
    
    Returns counts of total, valid, and invalid records.
    
    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists
        dataset_stmt = select(Dataset).where(
            and_(
                Dataset.id == dataset_id,
                Dataset.organization_id == organization_id,
                Dataset.deleted_at.is_(None)
            )
        )
        dataset_result = await db.execute(dataset_stmt)
        dataset = dataset_result.scalar_one_or_none()
        
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        # Get total count
        total_stmt = select(func.count()).select_from(Record).where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id
            )
        )
        total_result = await db.execute(total_stmt)
        total = total_result.scalar()
        
        # Get valid count
        valid_stmt = select(func.count()).select_from(Record).where(
            and_(
                Record.dataset_id == dataset_id,
                Record.organization_id == organization_id,
                Record.is_valid == True
            )
        )
        valid_result = await db.execute(valid_stmt)
        valid = valid_result.scalar()
        
        return RecordStats.calculate(dataset_id, total, valid)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get record stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


# Helper function to build filter conditions
def _build_filter_condition(column: str, operator: str, value: Any):
    """
    Build SQLAlchemy filter condition for JSONB data column.
    
    Args:
        column: Column name in the data JSONB field
        operator: Filter operator
        value: Value to filter by
    
    Returns:
        SQLAlchemy condition or None
    """
    if not column or not operator:
        return None
    
    try:
        op = FilterOperator(operator)
        
        if op == FilterOperator.EQUALS:
            return Record.data[column].as_string() == str(value)
        
        elif op == FilterOperator.NOT_EQUALS:
            return Record.data[column].as_string() != str(value)
        
        elif op == FilterOperator.GREATER_THAN:
            # Cast to numeric for comparison
            return cast(Record.data[column].as_string(), String).cast(text('FLOAT')) > float(value)
        
        elif op == FilterOperator.GREATER_THAN_OR_EQUAL:
            return cast(Record.data[column].as_string(), String).cast(text('FLOAT')) >= float(value)
        
        elif op == FilterOperator.LESS_THAN:
            return cast(Record.data[column].as_string(), String).cast(text('FLOAT')) < float(value)
        
        elif op == FilterOperator.LESS_THAN_OR_EQUAL:
            return cast(Record.data[column].as_string(), String).cast(text('FLOAT')) <= float(value)
        
        elif op == FilterOperator.CONTAINS:
            return Record.data[column].as_string().ilike(f"%{value}%")
        
        elif op == FilterOperator.STARTS_WITH:
            return Record.data[column].as_string().ilike(f"{value}%")
        
        elif op == FilterOperator.ENDS_WITH:
            return Record.data[column].as_string().ilike(f"%{value}")
        
        elif op == FilterOperator.IN:
            if isinstance(value, list):
                return Record.data[column].as_string().in_([str(v) for v in value])
            return None
        
        elif op == FilterOperator.NOT_IN:
            if isinstance(value, list):
                return ~Record.data[column].as_string().in_([str(v) for v in value])
            return None
        
        elif op == FilterOperator.IS_NULL:
            return Record.data[column].is_(None)
        
        elif op == FilterOperator.IS_NOT_NULL:
            return Record.data[column].isnot(None)
        
        else:
            logger.warning(f"Unknown filter operator: {operator}")
            return None
    
    except Exception as e:
        logger.warning(f"Failed to build filter condition: {e}")
        return None


# Export router
__all__ = ["router"]
